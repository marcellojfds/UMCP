from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest

from omp.adapters.mcp.hosted import HostedMCPAdapter, HostedToolCall, create_hosted_boundary_app
from omp.server.hosted_auth import HostedAuthenticator, VerifiedCredential

NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)


class SyntheticVerifier:
    def __init__(self, credentials: dict[str, VerifiedCredential | None]) -> None:
        self.credentials = credentials

    def verify(self, credential: str) -> VerifiedCredential | None:
        return self.credentials.get(credential)


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[HostedToolCall] = []

    async def call(self, command: HostedToolCall) -> dict[str, object]:
        self.calls.append(command)
        return {"accepted_for": str(command.principal.subject_id)}


def credential(**changes: object) -> VerifiedCredential:
    value = VerifiedCredential(
        subject_id=UUID("10000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("10000000-0000-0000-0000-000000000002"),
        membership_id=UUID("10000000-0000-0000-0000-000000000003"),
        credential_id=UUID("10000000-0000-0000-0000-000000000004"),
        scopes=frozenset({"memory:read", "memory:write", "memory:delete"}),
        auth_method="oidc",
        issuer="https://issuer.example.test",
        audience="https://umcp.example.test/mcp",
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=5),
    )
    return replace(value, **changes)


def app_for(credentials: dict[str, VerifiedCredential | None]) -> tuple[object, RecordingService]:
    service = RecordingService()
    auth = HostedAuthenticator(
        SyntheticVerifier(credentials),
        issuer="https://issuer.example.test",
        audience="https://umcp.example.test/mcp",
        clock=lambda: NOW,
    )
    return create_hosted_boundary_app(HostedMCPAdapter(service, auth)), service


def write_payload() -> dict[str, object]:
    return {
        "content": "The hosted boundary derives identity from verified claims.",
        "type": "lesson",
        "provenance": {"source_type": "conversation", "captured_at": "2026-08-24T12:00:00Z"},
        "idempotency_key": "hosted-boundary-test",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("authorization", "credentials", "status", "code"),
    [
        (None, {}, 401, "missing_credential"),
        ("Bearer malformed", {"malformed": None}, 401, "invalid_credential"),
        (
            "Bearer expired",
            {"expired": credential(expires_at=NOW - timedelta(seconds=1))},
            401,
            "invalid_credential",
        ),
        (
            "Bearer wrong-issuer",
            {"wrong-issuer": credential(issuer="https://elsewhere.example.test")},
            401,
            "invalid_credential",
        ),
        (
            "Bearer wrong-audience",
            {"wrong-audience": credential(audience="https://elsewhere.example.test/mcp")},
            401,
            "invalid_credential",
        ),
        (
            "Bearer missing-scope",
            {"missing-scope": credential(scopes=frozenset({"memory:read"}))},
            403,
            "insufficient_scope",
        ),
    ],
)
async def test_invalid_hosted_credentials_fail_closed_before_service_dispatch(
    authorization: str | None,
    credentials: dict[str, VerifiedCredential | None],
    status: int,
    code: str,
) -> None:
    app, service = app_for(credentials)
    headers = {"authorization": authorization} if authorization else {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/_hosted_boundary/memory.write", headers=headers, json=write_payload()
        )

    assert response.status_code == status
    assert response.json() == {"ok": False, "error": {"code": code}}
    assert service.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("authority_field", ["owner_id", "tenant_id"])
async def test_caller_authority_and_cross_tenant_selection_are_rejected_before_dispatch(
    authority_field: str,
) -> None:
    app, service = app_for({"valid": credential()})
    payload = write_payload()
    payload[authority_field] = "caller-selected-owner-or-tenant"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/_hosted_boundary/memory.write",
            headers={"authorization": "Bearer valid"},
            json=payload,
        )

    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": {"code": "invalid_request"}}
    assert service.calls == []


@pytest.mark.asyncio
async def test_verified_principal_reaches_service_without_caller_controlled_owner() -> None:
    verified = credential()
    app, service = app_for({"valid": verified})
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/_hosted_boundary/memory.write",
            headers={"authorization": "Bearer valid"},
            json=write_payload(),
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert len(service.calls) == 1
    call = service.calls[0]
    assert call.principal.subject_id == verified.subject_id
    assert call.principal.tenant_id == verified.tenant_id
    assert "owner_id" not in call.arguments
    assert "tenant_id" not in call.arguments
