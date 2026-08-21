from __future__ import annotations

import asyncio
import socket
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sse_starlette.sse import AppStatus

from omp.cloud import LocalDevelopmentTokenVerifier, Scope
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
    finally:
        server.should_exit = True
        await task
