from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

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
