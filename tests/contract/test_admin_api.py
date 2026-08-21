from fastapi.testclient import TestClient

from omp.cloud.admin import LocalMailboxAuth, create_admin_app


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
