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
        session = client.get("/api/session")
        assert session.status_code == 200
        assert session.json()["subject_id"]
        assert client.get("/api/auth/callback", params={"token": token}).status_code == 400
        assert client.post("/api/logout").status_code == 403
        assert client.post("/api/logout", headers={"x-umcp-csrf": csrf}).json() == {
            "status": "logged_out"
        }
        assert client.get("/api/session").status_code == 401


def test_magic_link_rate_limit_is_non_enumerating_and_does_not_store_email() -> None:
    auth = LocalMailboxAuth(magic_link_limit=2)
    with TestClient(create_admin_app(auth)) as client:
        responses = [
            client.post("/api/auth/magic-link", json={"email": "person@example.test"}).json()
            for _ in range(3)
        ]
    assert responses == [{"status": "accepted"}] * 3
    assert len(auth.outbox) == 2
    assert "person@example.test" not in repr(auth._magic_link_attempts)


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


def test_memory_list_has_bounded_pagination(tmp_path) -> None:
    auth = LocalMailboxAuth()
    runtime = create_demo_runtime(OMPSettings(demo_data_file=str(tmp_path / "admin-pages.json")))
    with TestClient(create_admin_app(auth, runtime)) as client:
        client.post("/api/auth/magic-link", json={"email": "person@example.test"})
        callback = client.get("/api/auth/callback", params={"token": auth.outbox[-1]["token"]})
        csrf = callback.json()["csrf"]
        for index in range(2):
            assert client.post(
                "/api/memories",
                headers={"x-umcp-csrf": csrf},
                json={
                    "content": f"paged memory {index}",
                    "type": "fact",
                    "provenance": {
                        "source_type": "user",
                        "captured_at": "2026-01-01T00:00:00Z",
                    },
                    "idempotency_key": f"page-{index}",
                },
            ).status_code == 200
        first = client.get("/api/memories", params={"query": "paged", "limit": 1}).json()
        assert first["count"] == 1
        assert first["next_cursor"] == 1
        second = client.get(
            "/api/memories", params={"query": "paged", "limit": 1, "cursor": 1}
        ).json()
        assert second["count"] == 1
        assert second["next_cursor"] is None


def test_admin_control_plane_uses_scoped_session_and_safe_receipts() -> None:
    auth = LocalMailboxAuth()
    with TestClient(create_admin_app(auth)) as client:
        client.post("/api/auth/magic-link", json={"email": "person@example.test"})
        callback = client.get("/api/auth/callback", params={"token": auth.outbox[-1]["token"]})
        csrf = callback.json()["csrf"]
        headers = {"x-umcp-csrf": csrf}

        connection = client.post(
            "/api/connections",
            headers=headers,
            json={"name": "local agent", "scopes": ["memory:read"]},
        ).json()["connection"]
        assert connection["status"] == "active"
        revoked = client.post(f"/api/connections/{connection['id']}/revoke", headers=headers)
        assert revoked.json()["connection"]["status"] == "revoked"

        credential = client.post(
            "/api/agent-credentials",
            headers=headers,
            json={"name": "worker", "scopes": ["memory:read"], "expires_in_seconds": 60},
        ).json()
        assert credential["token"].startswith("umcp_pat_")
        assert "token_digest" not in credential["credential"]
        listed_credentials = client.get("/api/agent-credentials").json()
        assert listed_credentials["count"] == 1
        assert listed_credentials["credentials"][0]["id"] == credential["credential"]["id"]
        assert "_token_digest" not in listed_credentials["credentials"][0]
        assert client.post(
            f"/api/agent-credentials/{credential['credential']['id']}/revoke", headers=headers
        ).status_code == 200

        exported = client.post("/api/exports", headers=headers).json()["receipt"]
        assert exported["kind"] == "tenant.export"
        export_status = client.get(f"/api/operations/{exported['id']}").json()
        assert export_status["receipt"]["status"] == "accepted"
        deleted = client.post("/api/account-deletions", headers=headers).json()["receipt"]
        assert deleted["kind"] == "account.deletion"
