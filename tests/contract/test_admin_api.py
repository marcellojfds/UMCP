from fastapi.testclient import TestClient

from omp.cloud.admin import LocalMailboxAuth, create_admin_app
from omp.config import OMPSettings
from omp.server.composition import create_demo_runtime


def test_local_magic_link_is_captured_single_use_and_csrf_protected() -> None:
    auth = LocalMailboxAuth()
    with TestClient(create_admin_app(auth)) as client:
        assert client.post(
            "/api/auth/magic-link", json={"email": "person@example.test"}
        ).json() == {"status": "accepted"}
        token = auth.outbox[-1]["token"]
        callback = client.get("/api/auth/callback", params={"token": token})
        assert callback.status_code == 200
        csrf = callback.json()["csrf"]
        assert client.get("/api/session").status_code == 200
        assert client.get("/api/auth/callback", params={"token": token}).status_code == 400
        assert client.post("/api/logout").status_code == 403
        assert client.post("/api/logout", headers={"x-umcp-csrf": csrf}).json() == {
            "status": "logged_out"
        }
        assert client.get("/api/session").status_code == 401


def test_session_scoped_memory_lifecycle_has_no_owner_input(tmp_path) -> None:
    auth = LocalMailboxAuth()
    runtime = create_demo_runtime(OMPSettings(demo_data_file=str(tmp_path / "admin.json")))
    with TestClient(create_admin_app(auth, runtime)) as client:
        client.post("/api/auth/magic-link", json={"email": "person@example.test"})
        callback = client.get("/api/auth/callback", params={"token": auth.outbox[-1]["token"]})
        csrf = callback.json()["csrf"]
        created = client.post(
            "/api/memories",
            headers={"x-umcp-csrf": csrf},
            json={
                "content": "tenant scoped memory",
                "type": "fact",
                "provenance": {"source_type": "user", "captured_at": "2026-01-01T00:00:00Z"},
                "idempotency_key": "create-1",
            },
        )
        assert created.status_code == 200
        memory = created.json()["memory"]
        assert "owner_id" not in memory
        listed = client.get("/api/memories", params={"query": "tenant"})
        assert listed.json()["count"] == 1
        forgotten = client.delete(
            f"/api/memories/{memory['id']}",
            params={"idempotency_key": "forget-1"},
            headers={"x-umcp-csrf": csrf},
        )
        assert forgotten.json()["status"] == "forgotten"
