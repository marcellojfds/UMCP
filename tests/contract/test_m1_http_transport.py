from __future__ import annotations

import json
from contextlib import AsyncExitStack

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from omp.adapters.mcp.http import (
    M1LocalAuth,
    create_m1_http_app,
    create_m1_server,
    create_m1_service,
)

M1_TOOLS = {
    "memory.capture": {"content", "type", "space", "provenance", "consent", "idempotency_key"},
    "memory.inbox.list": set(),
    "memory.inbox.confirm": {"id", "expected_version", "idempotency_key"},
    "memory.inbox.discard": {"id", "expected_version", "idempotency_key"},
    "memory.pin": {"id", "expected_version", "pinned", "idempotency_key"},
    "memory.recall": {"query", "context_space"},
    "memory.update": {"id", "expected_version", "patch", "idempotency_key"},
    "memory.forget": {"id", "idempotency_key"},
}


def test_m1_tools_have_frozen_names_strict_schemas_and_annotations() -> None:
    server = create_m1_server(create_m1_service(), M1LocalAuth())
    tools = server._tool_manager._tools
    assert set(tools) == set(M1_TOOLS)
    for name, required in M1_TOOLS.items():
        schema = tools[name].parameters
        assert schema["additionalProperties"] is False
        assert set(schema.get("required", [])) == required
        assert not {"tenant_id", "owner_id", "connection_id", "scopes"}.intersection(
            schema.get("properties", {})
        )

    assert tools["memory.recall"].annotations.readOnlyHint is True
    assert tools["memory.inbox.discard"].annotations.destructiveHint is True
    assert tools["memory.forget"].annotations.destructiveHint is True


def test_m1_local_controls_are_authenticated_and_connection_scoped() -> None:
    app = create_m1_http_app()
    with TestClient(app) as client:
        assert (
            client.post(
                "/local/revoke", json={"connection_id": "conn-chatgpt-sim", "client": "chatgpt-sim"}
            ).status_code
            == 401
        )
        response = client.post(
            "/local/revoke",
            headers={"authorization": "Bearer m1-fixture-claude-sim"},
            json={"connection_id": "conn-chatgpt-sim", "client": "chatgpt-sim"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "revoked"}
        denied = client.post(
            "/local/revoke",
            headers={"authorization": "Bearer m1-fixture-chatgpt-sim-b"},
            json={"connection_id": "conn-chatgpt-sim", "client": "chatgpt-sim"},
        )
        assert denied.status_code == 403


def test_m1_official_mcp_path_does_not_redirect_or_downgrade_https() -> None:
    """Freeze the Cloud Run TLS-termination regression with synthetic headers."""
    app = create_m1_http_app()
    request = {
        "jsonrpc": "2.0",
        "id": "initialize-over-https",
        "method": "initialize",
        "params": {},
    }
    headers = {
        "authorization": "Bearer m1-fixture-chatgpt-sim",
        "accept": "application/json, text/event-stream",
        "x-forwarded-proto": "https",
        "origin": "https://synthetic-client.invalid",
    }
    with TestClient(
        app, base_url="https://mcp.synthetic.invalid", follow_redirects=False
    ) as client:
        response = client.post("/mcp", headers=headers, json=request)
        assert response.status_code == 200
        assert "location" not in response.headers
        assert response.headers["mcp-session-id"]

        trailing = client.post("/mcp/", headers=headers, json=request)
        assert trailing.status_code == 404
        assert "location" not in trailing.headers


@pytest.mark.asyncio
async def test_m1_streamable_http_core_lifecycle_is_rerunnable() -> None:
    app = create_m1_http_app()
    server = app.state.m1_server
    async with server.session_manager.run():
        transport = httpx.ASGITransport(app=app)

        async def call(token: str, name: str, arguments: dict[str, object]) -> dict[str, object]:
            async with AsyncExitStack() as stack:
                client = await stack.enter_async_context(
                    httpx.AsyncClient(
                        transport=transport,
                        base_url="http://testserver",
                        headers={
                            "authorization": f"Bearer {token}",
                            "accept": "application/json, text/event-stream",
                        },
                    )
                )
                read_stream, write_stream, _ = await stack.enter_async_context(
                    streamable_http_client("http://testserver/mcp", http_client=client)
                )
                session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
                await session.initialize()
                result = await session.call_tool(name, arguments)
                return json.loads(result.content[0].text)

        forged = await call(
            "m1-fixture-chatgpt-sim",
            "memory.capture",
            {
                "content": "authority-negative",
                "type": "lesson",
                "space": "MBA",
                "provenance": {
                    "source_type": "conversation",
                    "source_client": "chatgpt-sim",
                    "captured_at": "2026-08-22T12:00:00Z",
                },
                "consent": {
                    "mode": "assisted",
                    "consent_id": "consent-forged",
                    "reason_code": "user_requested_memory",
                    "policy_version": "m1-local-1",
                    "granted_at": "2026-08-22T12:00:00Z",
                },
                "idempotency_key": "transport-forged",
                "owner_id": "forged-owner",
            },
        )
        assert forged["error"]["code"] == "validation_error"
        captured = await call(
            "m1-fixture-chatgpt-sim",
            "memory.capture",
            {
                "content": (
                    "Poorly designed incentives make teams optimize the metric, not the outcome."
                ),
                "type": "lesson",
                "space": "MBA",
                "provenance": {
                    "source_type": "conversation",
                    "source_client": "chatgpt-sim",
                    "source_connection_id": "conn-chatgpt-sim",
                    "captured_at": "2026-08-22T12:00:00Z",
                },
                "consent": {
                    "mode": "assisted",
                    "consent_id": "consent-test",
                    "reason_code": "user_requested_memory",
                    "policy_version": "m1-local-1",
                    "granted_at": "2026-08-22T12:00:00Z",
                },
                "idempotency_key": "transport-capture",
            },
        )
        memory = captured["data"]["memory"]
        assert memory["state"] == "candidate"
        empty = await call(
            "m1-fixture-chatgpt-sim",
            "memory.recall",
            {"query": "incentives outcome", "context_space": "MBA"},
        )
        assert empty["data"] == {"count": 0, "memories": []}
        confirmed = await call(
            "m1-fixture-chatgpt-sim",
            "memory.inbox.confirm",
            {
                "id": memory["id"],
                "expected_version": memory["version"],
                "idempotency_key": "transport-confirm",
            },
        )
        assert confirmed["data"]["memory"]["state"] == "confirmed"
        recalled = await call(
            "m1-fixture-claude-sim",
            "memory.recall",
            {
                "query": (
                    "Why did the work team increase closed tickets while "
                    "customer satisfaction fell?"
                ),
                "context_space": "Work",
                "include_spaces": ["MBA"],
            },
        )
        assert recalled["data"]["count"] == 1
        assert recalled["data"]["memories"][0]["reason_retrieved"] == (
            "explicit_cross_space_semantic_match"
        )
        tenant_b = await call(
            "m1-fixture-chatgpt-sim-b",
            "memory.recall",
            {"query": "incentives outcome", "context_space": "MBA"},
        )
        assert tenant_b["data"] == {"count": 0, "memories": []}
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            revoked = await client.post(
                "/local/revoke",
                headers={"authorization": "Bearer m1-fixture-claude-sim"},
                json={"connection_id": "conn-chatgpt-sim", "client": "chatgpt-sim"},
            )
            assert revoked.status_code == 200
        denied = await call(
            "m1-fixture-chatgpt-sim",
            "memory.capture",
            {
                "content": "must not persist",
                "type": "lesson",
                "space": "MBA",
                "provenance": {
                    "source_type": "conversation",
                    "source_client": "chatgpt-sim",
                    "captured_at": "2026-08-22T12:00:00Z",
                },
                "consent": {
                    "mode": "assisted",
                    "consent_id": "consent-denied",
                    "reason_code": "user_requested_memory",
                    "policy_version": "m1-local-1",
                    "granted_at": "2026-08-22T12:00:00Z",
                },
                "idempotency_key": "transport-revoked",
            },
        )
        assert denied["error"]["code"] == "connection_revoked"
        forgotten = await call(
            "m1-fixture-claude-sim",
            "memory.forget",
            {"id": memory["id"], "idempotency_key": "transport-forget"},
        )
        assert forgotten["data"]["status"] == "forgotten"
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"authorization": "Bearer m1-fixture-claude-sim"},
        ) as client:
            restored = await client.post(
                "/local/restore",
                json={
                    "format": "omp.export.v0",
                    "exported_at": "2026-08-22T12:00:00Z",
                    "includes_embeddings": False,
                    "memories": [memory],
                },
            )
            assert restored.json() == {"status": "restore_blocked_by_tombstone"}
