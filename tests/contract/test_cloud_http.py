from __future__ import annotations

import asyncio
import json
import os
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
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
from omp.server.composition import create_cloud_demo_runtime, create_demo_runtime, create_runtime
from omp.server.oauth import OAuthError
from omp.server.official import (
    RejectUnconfiguredOIDCVerifier,
    create_cloud_http_app,
    create_cloud_server,
)


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
    assert "memory.capture" in tools
    assert "owner_id" not in tools["memory.capture"].parameters["properties"]
    assert tools["memory.capture"].meta["securitySchemes"][0]["type"] == "oauth2"


@pytest.mark.parametrize("forged_field", ["owner_id", "tenant_id"])
def test_cloud_mcp_rejects_client_supplied_authority(tmp_path, forged_field: str) -> None:
    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "cloud.json")), kms_master_key=b"k" * 32
    )
    app = create_cloud_http_app(runtime, verifier())
    with TestClient(app, base_url="https://local.umcp.invalid") as client:
        response = client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"arguments": {forged_field: "forged"}},
            },
        )
    assert response.status_code == 400


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
        assert "resource_metadata=" in missing.headers["www-authenticate"]
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


def test_oauth_form_endpoints_receive_starlette_request_objects(tmp_path) -> None:
    """Regression coverage for postponed annotations on FastAPI request inputs."""

    class StubOAuthServer:
        config = SimpleNamespace(
            issuer="https://local.umcp.invalid",
            clients={"test-client": "https://local.umcp.invalid/readyz"},
        )

        def metadata(self) -> dict[str, str]:
            return {"issuer": self.config.issuer}

        async def token(self, form: dict[str, str]) -> dict[str, str]:
            raise OAuthError("unsupported_grant_type")

        async def revoke(self, token: str) -> None:
            return None

    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "cloud.json")), kms_master_key=b"k" * 32
    )
    app = create_cloud_http_app(runtime, verifier(), oauth_server=StubOAuthServer())
    with TestClient(app, base_url="https://local.umcp.invalid") as client:
        assert client.post("/token", content="").status_code == 400
        assert client.post("/revoke", content="").status_code == 200
        # Audit runner is disabled by default
        assert client.get("/oauth/audit-runner").status_code == 404
        assert client.get("/oauth/audit/callback").status_code == 404
        assert client.post("/oauth/audit/start", json={}).status_code == 404


def test_hosted_login_page_is_pkce_bound_and_rejects_client_authority(tmp_path) -> None:
    """The hosted sign-in page is an OAuth handoff, never a tenant selector."""

    class StubOAuthServer:
        config = SimpleNamespace(
            issuer="https://local.umcp.invalid",
            clients={"test-client": "https://client.example.test/callback"},
        )

        def metadata(self) -> dict[str, str]:
            return {"issuer": self.config.issuer}

        async def token(self, form: dict[str, str]) -> dict[str, str]:
            raise OAuthError("unsupported_grant_type")

        async def revoke(self, token: str) -> None:
            return None

    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "cloud.json")), kms_master_key=b"k" * 32
    )
    app = create_cloud_http_app(runtime, verifier(), oauth_server=StubOAuthServer())
    with TestClient(app, base_url="https://local.umcp.invalid") as client:
        landing = client.get("/login")
        assert landing.status_code == 200
        assert "Continue with Google" in landing.text
        assert "owner_id" not in landing.text
        assert "tenant_id" not in landing.text
        assert landing.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in landing.headers["content-security-policy"]

        start = client.get(
            "/login",
            params={
                "response_type": "code",
                "client_id": "test-client",
                "redirect_uri": "https://client.example.test/callback",
                "scope": "memory:read",
                "state": "client-state",
                "code_challenge": "a" * 43,
                "code_challenge_method": "S256",
            },
        )
        assert start.status_code == 200
        assert 'href="/authorize?' in start.text
        assert "code_challenge_method=S256" in start.text
        assert client.get("/login?owner_id=forged").status_code == 400
        assert client.get("/login?tenant_id=forged").status_code == 400


def test_portal_google_login_reuses_oauth_identity_and_lists_memories(tmp_path) -> None:
    local = verifier()
    portal_access = token(
        local, {Scope.MEMORY_READ, Scope.MEMORY_WRITE, Scope.MEMORY_DELETE}
    )
    refreshed_access = token(
        local, {Scope.MEMORY_READ, Scope.MEMORY_WRITE, Scope.MEMORY_DELETE}
    )

    class StubOAuthServer:
        config = SimpleNamespace(
            issuer="https://local.umcp.invalid",
            clients={},
        )
        client_state = ""

        def metadata(self) -> dict[str, object]:
            return {
                "issuer": self.config.issuer,
                "authorization_response_iss_parameter_supported": True,
            }

        async def begin(
            self,
            client_id: str,
            redirect_uri: str,
            scope: str,
            state: str,
            challenge: str,
            method: str,
            resource: str | None = None,
        ) -> str:
            self.client_state = state
            assert client_id == "umcp-portal"
            assert redirect_uri == "https://local.umcp.invalid/portal/callback"
            assert method == "S256"
            assert resource == "https://local.umcp.invalid/mcp"
            return "https://accounts.google.com/o/oauth2/v2/auth?state=upstream"

        async def callback(self, code: str, state: str) -> tuple[str, str, str]:
            return (
                "https://local.umcp.invalid/portal/callback",
                "authorization-code",
                self.client_state,
            )

        async def token(self, form: dict[str, str]) -> dict[str, str]:
            assert form["client_id"] == "umcp-portal"
            if form["grant_type"] == "refresh_token":
                assert form["refresh_token"] == "portal-refresh"
                return {"access_token": refreshed_access, "refresh_token": "rotated-refresh"}
            return {"access_token": portal_access, "refresh_token": "portal-refresh"}

        async def revoke(self, token_value: str) -> None:
            local.revoke(token_value)

        async def verify_token(self, token_value: str):
            return await local.verify_token(token_value)

    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "portal.json")), kms_master_key=b"k" * 32
    )
    root = Path(__file__).parents[2]
    app = create_cloud_http_app(
        runtime,
        local,
        oauth_server=StubOAuthServer(),
        web_directory=root / "apps" / "web",
    )
    with TestClient(app, base_url="https://local.umcp.invalid") as client:
        start = client.get("/portal/login", follow_redirects=False)
        assert start.status_code == 302
        assert start.headers["location"].startswith("https://accounts.google.com/")
        assert "HttpOnly" in start.headers["set-cookie"]

        provider = client.get(
            "/oauth/callback?code=google-code&state=upstream", follow_redirects=False
        )
        assert provider.status_code == 302
        callback = client.get(provider.headers["location"], follow_redirects=False)
        assert callback.status_code == 302
        assert callback.headers["location"] == "/portal/#/memories"
        assert any(
            "umcp_portal_refresh" in value
            for value in callback.headers.get_list("set-cookie")
        )

        session = client.get("/portal/api/session")
        assert session.status_code == 200
        memories = client.get("/portal/api/memories")
        assert memories.status_code == 200
        assert memories.json() == {"memories": [], "count": 0}

        local.revoke(portal_access)
        assert client.get("/portal/api/session").status_code == 401
        assert client.post("/portal/api/refresh").status_code == 200
        assert client.get("/portal/api/session").status_code == 200

        shell = client.get("/portal/")
        assert shell.status_code == 200
        assert "no-store" in shell.headers["cache-control"]
        assert 'src="./src/app.js?v=portal-20260902-2"' in shell.text
        portal_script = client.get("/portal/src/app.js?v=portal-20260902-2")
        assert portal_script.status_code == 200
        assert "no-store" in portal_script.headers["cache-control"]
        bootstrap = client.get("/portal/admin-config.js")
        assert 'window.__UMCP_GOOGLE_LOGIN_URL__ = "/portal/login"' in bootstrap.text


def test_oauth_audit_runner_requires_flag_and_exact_client(tmp_path) -> None:
    """Audit runner routes only exist when flag is enabled and exactly one matching client is configured."""

    class StubOAuthServer:
        def __init__(self, clients: dict[str, str]) -> None:
            self.config = SimpleNamespace(
                issuer="https://local.umcp.invalid",
                clients=clients,
            )

        def metadata(self) -> dict[str, str]:
            return {"issuer": self.config.issuer}

        async def begin(self, client_id: str, redirect_uri: str, scope: str, state: str, challenge: str, method: str) -> str:
            return f"https://accounts.google.com/o/oauth2/v2/auth?client_id=google&state={state}"

        async def callback(self, code: str, state: str) -> tuple[str, str, str]:
            return "https://local.umcp.invalid/oauth/audit/callback", "ac_test_123", "st_test_456"

        async def token(self, form: dict[str, str]) -> dict[str, str]:
            return {"access_token": "at_test", "refresh_token": "rt_test"}

        async def revoke(self, token: str) -> None:
            return None

    # Case 1: Flag enabled, but no matching client redirect
    runtime_mismatch = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "c1.json"), oauth_audit_runner_enabled=True),
        kms_master_key=b"k" * 32,
    )
    oauth_mismatch = StubOAuthServer({"audit-client": "https://local.umcp.invalid/wrong/callback"})
    app_mismatch = create_cloud_http_app(runtime_mismatch, verifier(), oauth_server=oauth_mismatch)
    with TestClient(app_mismatch, base_url="https://local.umcp.invalid") as client:
        assert client.get("/oauth/audit-runner").status_code == 404

    # Case 2: Flag enabled, exact matching client
    runtime_valid = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "c2.json"), oauth_audit_runner_enabled=True),
        kms_master_key=b"k" * 32,
    )
    oauth_valid = StubOAuthServer({"audit-client": "https://local.umcp.invalid/oauth/audit/callback"})
    app_valid = create_cloud_http_app(runtime_valid, verifier(), oauth_server=oauth_valid)
    with TestClient(app_valid, base_url="https://local.umcp.invalid") as client:
        runner_resp = client.get("/oauth/audit-runner")
        assert runner_resp.status_code == 200
        assert runner_resp.headers["cache-control"] == "no-store"
        assert runner_resp.headers["pragma"] == "no-cache"
        assert runner_resp.headers["referrer-policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in runner_resp.headers["content-security-policy"]
        assert "localStorage" not in runner_resp.text

        callback_resp = client.get("/oauth/audit/callback")
        assert callback_resp.status_code == 200
        assert callback_resp.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in callback_resp.headers["content-security-policy"]
        assert "audit-client" in callback_resp.text
        assert "localStorage" not in callback_resp.text

        start_resp = client.post("/oauth/audit/start", json={"state": "s" * 10, "code_challenge": "c" * 43})
        assert start_resp.status_code == 200
        assert "https://accounts.google.com" in start_resp.json()["redirect"]

        # OAuth callback uses fragment '#' for audit redirect to avoid server URL logging of authorization code
        cb_redirect = client.get("/oauth/callback?code=google_code&state=google_state", follow_redirects=False)
        assert cb_redirect.status_code == 302
        loc = cb_redirect.headers["location"]
        assert loc.startswith("https://local.umcp.invalid/oauth/audit/callback#code=")
        assert "?" not in loc
        assert "iss=https%3A%2F%2Flocal.umcp.invalid" in loc


def test_cloud_process_stays_live_but_unready_when_postgres_is_unavailable() -> None:
    """A dependency outage is readiness failure, not a Cloud Run startup crash."""
    runtime = create_runtime(
        OMPSettings(
            backend="postgres",
            database_url="postgresql+asyncpg://127.0.0.1:1/umcp",
        )
    )
    app = create_cloud_http_app(runtime, RejectUnconfiguredOIDCVerifier())
    with TestClient(app, base_url="https://local.umcp.invalid") as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/readyz").status_code == 503
        assert client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        ).status_code == 401


def test_cloud_official_mcp_path_does_not_redirect_or_downgrade_https(tmp_path) -> None:
    """Keep the public `/mcp` route exact behind a synthetic TLS proxy."""
    runtime = create_cloud_demo_runtime(
        OMPSettings(demo_data_file=str(tmp_path / "cloud.json")), kms_master_key=b"k" * 32
    )
    local = verifier()
    app = create_cloud_http_app(runtime, local)
    headers = {
        "authorization": f"Bearer {token(local, {Scope.MEMORY_READ})}",
        "accept": "application/json, text/event-stream",
        "x-forwarded-proto": "https",
        "origin": "https://local.umcp.invalid",
    }
    request = {
        "jsonrpc": "2.0",
        "id": "initialize-over-https",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "umcp-contract", "version": "1"},
        },
    }
    # Model the internal HTTP hop after a TLS terminator without permitting
    # the application/router to construct a downgrade redirect.
    with TestClient(
        app, base_url="http://local.umcp.invalid", follow_redirects=False
    ) as client:
        response = client.post("/mcp", headers=headers, json=request)
        assert response.status_code == 200
        assert "location" not in response.headers
        # The hosted transport is stateless, so a successful initialize is
        # streamed and intentionally does not establish a session header.
        assert "mcp-session-id" not in response.headers

        trailing = client.post("/mcp/", headers=headers, json=request)
        assert trailing.status_code == 404
        assert "location" not in trailing.headers


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
        assert 'src="./admin-config.js?v=portal-20260831-3"' in shell.text
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
        surviving_credential = client.post(
            "/admin/api/agent-credentials",
            headers=headers,
            json={"name": "delete revocation", "scopes": ["memory:read"]},
        ).json()["token"]
        deletion = client.post("/admin/api/account-deletions", headers=headers).json()
        assert deletion["receipt"]["status"] == "done"
        assert deletion["deleted_memories"] == 1
        assert client.get("/admin/api/session").status_code == 401
        assert client.post(
            "/mcp",
            headers={
                "authorization": f"Bearer {surviving_credential}",
                "accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {}},
        ).status_code == 401

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
                    capture = next(tool for tool in tools if tool.name == "memory.capture")
                    assert "owner_id" not in capture.inputSchema["properties"]
                    assert capture.meta["securitySchemes"][0]["type"] == "oauth2"

                    captured = await client.call_tool(
                        "memory.capture",
                        {
                            "content": "The user prefers concise weekly summaries",
                            "type": "preference",
                            "reason": "The user explicitly asked ChatGPT to remember this.",
                        },
                    )
                    assert "prefers concise weekly summaries" in captured.content[0].text
                    assert "owner_id" not in captured.content[0].text

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
