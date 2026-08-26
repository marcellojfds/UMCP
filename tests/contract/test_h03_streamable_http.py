from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from omp.cloud.security import Principal, Scope
from omp.config import OMPSettings
from omp.server.composition import create_demo_runtime
from omp.server.streamable_http import create_in_process_streamable_http_app


def principal() -> Principal:
    return Principal(
        subject_id=UUID("10000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("10000000-0000-0000-0000-000000000002"),
        membership_id=UUID("10000000-0000-0000-0000-000000000003"),
        credential_id=UUID("10000000-0000-0000-0000-000000000004"),
        scopes=frozenset({Scope.MEMORY_READ, Scope.MEMORY_WRITE, Scope.MEMORY_DELETE}),
        auth_method="synthetic-verified",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def test_h03_exact_mcp_lifecycle_uses_principal_only(tmp_path) -> None:
    runtime = create_demo_runtime(OMPSettings(demo_data_file=str(tmp_path / "mcp.json")))
    app = create_in_process_streamable_http_app(runtime, principal(), readiness=lambda: True)
    with TestClient(app, base_url="http://testserver") as client:
        assert {route.path for route in app.routes} >= {"/mcp", "/healthz", "/readyz"}
        assert client.post("/mcp/").status_code == 404
        assert client.get("/readyz").json() == {"status": "ready"}
        initialized = client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": "init", "method": "initialize", "params": {}}
        )
        assert initialized.status_code == 200
        session = initialized.headers["mcp-session-id"]
        assert initialized.json()["id"] == "init"
        headers = {"mcp-session-id": session}
        listed = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert [tool["name"] for tool in listed.json()["result"]["tools"]] == [
            "memory.write",
            "memory.search",
            "memory.update",
            "memory.forget",
        ]
        called = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "memory.write",
                    "arguments": {
                        "content": "synthetic H03 memory",
                        "type": "fact",
                        "provenance": {
                            "source_type": "test",
                            "captured_at": "2026-01-01T00:00:00Z",
                        },
                        "idempotency_key": "h03-1",
                    },
                },
            },
        )
        assert called.status_code == 200
        assert called.json()["id"] == "call-1"
        assert '"owner_id"' not in called.text
        assert (
            client.post(
                "/mcp",
                headers=headers,
                json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            ).status_code
            == 200
        )


def test_h03_fail_closed_boundary_and_truthful_readiness(tmp_path) -> None:
    runtime = create_demo_runtime(OMPSettings(demo_data_file=str(tmp_path / "mcp.json")))
    app = create_in_process_streamable_http_app(runtime, principal())
    with TestClient(app, base_url="http://testserver") as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/readyz").status_code == 503
        assert (
            client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            ).status_code
            == 404
        )
        initialized = client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        headers = {"mcp-session-id": initialized.headers["mcp-session-id"]}
        forged = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "memory.search",
                    "arguments": {"query": "x", "owner_id": "forged"},
                },
            },
        )
        assert forged.status_code == 400
        assert (
            client.post(
                "/mcp",
                headers=headers,
                json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/mcp",
                headers={"host": "evil.example", **headers},
                json={"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
            ).status_code
            == 400
        )
