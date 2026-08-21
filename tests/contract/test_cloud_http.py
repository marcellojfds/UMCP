from __future__ import annotations

import asyncio
import json
import os
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sse_starlette.sse import AppStatus

from omp.cloud import LocalAgentCredentialVerifier, LocalDevelopmentTokenVerifier, Scope
from omp.cloud.admin import LocalMailboxAuth, create_admin_app
from omp.config import OMPSettings
from omp.server.composition import create_cloud_demo_runtime, create_demo_runtime
from omp.server.official import create_cloud_http_app, create_cloud_server


def verifier() -> LocalDevelopmentTokenVerifier:
    return LocalDevelopmentTokenVerifier(
        secret=b"t" * 32,
        issuer="https://local.umcp.invalid",
        audience="https://local.umcp.invalid/mcp",
    )


def token(value: LocalDevelopmentTokenVerifier, scopes: set[Scope]) -> str:
    return value.issue(
        subject=uuid4(),
        tenant_id=uuid4(),
        membership_id=uuid4(),
        credential_id=uuid4(),
        scopes=scopes,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def test_cloud_tools_reject_owner_id_and_have_security_annotations(tmp_path) -> None:
    runtime = create_demo_runtime(OMPSettings(demo_data_file=str(tmp_path / "cloud.json")))
    server = create_cloud_server(runtime, verifier())
    tools = server._tool_manager._tools
    assert "owner_id" not in tools["memory.write"].parameters["properties"]
    assert tools["memory.search"].annotations.readOnlyHint is True
    assert tools["memory.forget"].annotations.destructiveHint is True


def test_cloud_http_is_fail_closed_and_health_is_separate(tmp_path) -> None:
    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "cloud.json")), kms_master_key=b"k" * 32
    )
    local = verifier()
    app = create_cloud_http_app(runtime, local)
    with TestClient(app, base_url="https://local.umcp.invalid") as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        missing = client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert missing.status_code == 401
        bad = client.post(
            "/mcp",
            headers={
                "authorization": "Bearer bad",
                "accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert bad.status_code == 401
        good = client.post(
            "/mcp",
            headers={
                "authorization": f"Bearer {token(local, {Scope.MEMORY_READ})}",
                "accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert good.status_code == 200
        revoked_token = token(local, {Scope.MEMORY_READ})
        local.revoke(revoked_token)
        revoked = client.post(
            "/mcp",
            headers={
                "authorization": f"Bearer {revoked_token}",
                "accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert revoked.status_code == 401


def test_local_cloud_composition_serves_admin_and_web_before_mcp_mount(tmp_path) -> None:
    """The browser shell can reach only the same-origin Admin API in local mode."""
    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "cloud.json")), kms_master_key=b"k" * 32
    )
    auth = LocalMailboxAuth()
    root = Path(__file__).parents[2]
    pat_verifier = LocalAgentCredentialVerifier(
        auth, issuer="https://local.umcp.invalid", audience="https://local.umcp.invalid/mcp"
    )
    app = create_cloud_http_app(
        runtime,
        pat_verifier,
        admin_app=create_admin_app(auth, runtime),
        web_directory=root / "apps" / "web",
    )
    with TestClient(app, base_url="https://local.umcp.invalid") as client:
        shell = client.get("/web/")
        assert shell.status_code == 200
        assert 'src="./admin-config.js"' in shell.text
        bootstrap = client.get("/web/admin-config.js")
        assert bootstrap.status_code == 200
        assert bootstrap.text == 'window.__UMCP_ADMIN_API_BASE_URL__ = "/admin";\n'
        assert "no-store" in bootstrap.headers["cache-control"]

        assert client.post(
            "/admin/api/auth/magic-link", json={"email": "person@example.test"}
        ).json() == {"status": "accepted"}
        callback = client.get(
            "/admin/api/auth/callback", params={"token": auth.outbox[-1]["token"]}
        )
        assert callback.status_code == 200
        assert client.get("/admin/api/session").status_code == 200
        csrf = callback.json()["csrf"]
        headers = {"x-umcp-csrf": csrf}
        created = client.post(
            "/admin/api/memories",
            headers=headers,
            json={
                "content": "local web lifecycle memory",
                "type": "fact",
                "provenance": {"source_type": "user", "captured_at": "2026-01-01T00:00:00Z"},
                "idempotency_key": "web-lifecycle-create",
            },
        )
        assert created.status_code == 200
        memory = created.json()["memory"]
        assert "owner_id" not in memory
        assert client.patch(
            f"/admin/api/memories/{memory['id']}",
            headers=headers,
            json={
                "expected_version": memory["version"],
                "patch": {"content": "local web lifecycle updated"},
                "idempotency_key": "web-lifecycle-update",
            },
        ).status_code == 200
        connection = client.post(
            "/admin/api/connections",
            headers=headers,
            json={"name": "local browser", "scopes": ["memory:read"]},
        ).json()["connection"]
        assert client.post(
            f"/admin/api/connections/{connection['id']}/revoke", headers=headers
        ).json()["connection"]["status"] == "revoked"
        credential = client.post(
            "/admin/api/agent-credentials",
            headers=headers,
            json={"name": "local mcp", "scopes": ["memory:read"]},
        ).json()
        raw_pat = credential["token"]
        assert client.post(
            "/mcp",
            headers={
                "authorization": f"Bearer {raw_pat}",
                "accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        ).status_code == 200
        assert client.post(
            f"/admin/api/agent-credentials/{credential['credential']['id']}/revoke",
            headers=headers,
        ).status_code == 200
        assert client.post(
            "/mcp",
            headers={
                "authorization": f"Bearer {raw_pat}",
                "accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}},
        ).status_code == 401
        assert client.delete(
            f"/admin/api/memories/{memory['id']}",
            params={"idempotency_key": "web-lifecycle-forget"},
            headers=headers,
        ).json()["status"] == "forgotten"
        export = client.post("/admin/api/exports", headers=headers).json()["receipt"]
        assert client.get(f"/admin/api/operations/{export['id']}").status_code == 200
        assert client.post(
            "/admin/api/memories",
            headers=headers,
            json={
                "content": "account deletion canary",
                "type": "fact",
                "provenance": {"source_type": "user", "captured_at": "2026-01-01T00:00:00Z"},
                "idempotency_key": "account-deletion-create",
            },
        ).status_code == 200
        deletion = client.post("/admin/api/account-deletions", headers=headers).json()
        assert deletion["receipt"]["status"] == "done"
        assert deletion["deleted_memories"] == 1
        assert client.get("/admin/api/memories", params={"query": "account"}).json()["count"] == 0

        # The mounted application does not weaken the hosted MCP boundary.
        assert client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        ).status_code == 401


@pytest.mark.asyncio
async def test_cloud_http_calls_tools_with_verified_tenant_principal(tmp_path) -> None:
    """Exercise discovery and a complete hosted memory lifecycle over `/mcp`."""
    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "cloud.json")), kms_master_key=b"k" * 32
    )
    local = verifier()
    access_token = token(local, {Scope.MEMORY_READ, Scope.MEMORY_WRITE, Scope.MEMORY_DELETE})
    headers = {
        "authorization": f"Bearer {access_token}",
        "accept": "application/json, text/event-stream",
        "host": "local.umcp.invalid",
    }

    app = create_cloud_http_app(runtime, local)
    # TestClient in the preceding contract owns an event loop. sse-starlette
    # keeps this event process-global, so make the loopback server bind it anew.
    AppStatus.should_exit_event = None
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(server.serve())
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                async with httpx.AsyncClient() as health_client:
                    if (await health_client.get(f"{base_url}/healthz")).status_code == 200:
                        break
            except httpx.ConnectError:
                await asyncio.sleep(0.02)
        else:
            pytest.fail("local MCP server did not become ready")

        async with httpx.AsyncClient(headers=headers) as http_client:
            async with streamable_http_client(
                f"{base_url}/mcp", http_client=http_client
            ) as streams:
                read_stream, write_stream, _ = streams
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()
                    listed = await client.list_tools()
                    tools = listed.tools
                    write = next(tool for tool in tools if tool.name == "memory.write")
                    assert "owner_id" not in write.inputSchema["properties"]

                    written = await client.call_tool(
                        "memory.write",
                        {
                            "content": "remote authenticated memory",
                            "type": "fact",
                            "provenance": {
                                "source_type": "user",
                                "captured_at": "2026-01-01T00:00:00Z",
                            },
                            "idempotency_key": "http-write-1",
                        },
                    )
                    payload = written.content[0].text
                    assert "remote authenticated memory" in payload
                    assert "owner_id" not in payload

                    searched = await client.call_tool(
                        "memory.search", {"query": "authenticated"}
                    )
                    assert "remote authenticated memory" in searched.content[0].text

            forged_owner = await http_client.post(
                f"{base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 99,
                    "method": "tools/call",
                    "params": {
                        "name": "memory.write",
                        "arguments": {
                            "content": "must not be accepted",
                            "type": "fact",
                            "provenance": {"source_type": "user"},
                            "idempotency_key": "forged-owner-1",
                            "owner_id": "cloud:00000000-0000-0000-0000-000000000000:forged",
                        },
                    },
                },
            )
            assert forged_owner.status_code == 400

        read_only_headers = {
            **headers,
            "authorization": f"Bearer {token(local, {Scope.MEMORY_READ})}",
        }
        async with httpx.AsyncClient(headers=read_only_headers) as read_only_http:
            async with streamable_http_client(
                f"{base_url}/mcp", http_client=read_only_http
            ) as streams:
                read_stream, write_stream, _ = streams
                async with ClientSession(read_stream, write_stream) as read_only_client:
                    await read_only_client.initialize()
                    denied = await read_only_client.call_tool(
                        "memory.write",
                        {
                            "content": "scope must deny this",
                            "type": "fact",
                            "provenance": {"source_type": "user"},
                            "idempotency_key": "scope-denied-1",
                        },
                    )
                    assert denied.isError is True
    finally:
        server.should_exit = True
        await task


@pytest.mark.asyncio
async def test_conformance_runner_executes_against_local_mcp_gateway(tmp_path) -> None:
    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "conformance.json")), kms_master_key=b"k" * 32
    )
    local = verifier()
    access_token = token(local, {Scope.MEMORY_READ, Scope.MEMORY_WRITE, Scope.MEMORY_DELETE})
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    app = create_cloud_http_app(runtime, local, allowed_hosts=[f"127.0.0.1:{port}"])
    AppStatus.should_exit_event = None
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(server.serve())
    base_url = f"http://127.0.0.1:{port}"
    root = Path(__file__).parents[2]
    try:
        for _ in range(50):
            try:
                async with httpx.AsyncClient() as health_client:
                    if (await health_client.get(f"{base_url}/healthz")).status_code == 200:
                        break
            except httpx.ConnectError:
                await asyncio.sleep(0.02)
        else:
            pytest.fail("local MCP server did not become ready")
        process = await asyncio.create_subprocess_exec(
            "node",
            "examples/conformance/runner.mjs",
            "./examples/conformance/mcp-http-adapter.mjs",
            cwd=root,
            env={
                **os.environ,
                "UMCP_MCP_URL": f"{base_url}/mcp",
                "UMCP_ACCESS_TOKEN": access_token,
            },
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        assert process.returncode == 0, stderr.decode()
        result = json.loads(stdout)
        assert result["status"] == "pass"
        assert "Synthetic conformance memory" not in stdout.decode()
    finally:
        server.should_exit = True
        await task
