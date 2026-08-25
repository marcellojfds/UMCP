"""Adversarial composition tests for the local hosted gateway seam."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest

from omp.adapters.mcp.hosted import HostedToolCall
from omp.server.hosted_auth import VerifiedCredential
from omp.server.hosted_gateway import create_local_hosted_gateway

NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)


class SyntheticVerifier:
    """A verified-claims fixture; it never parses or creates credentials."""

    def __init__(self, credentials: dict[str, VerifiedCredential | None]) -> None:
        self.credentials = credentials

    def verify(self, credential: str) -> VerifiedCredential | None:
        return self.credentials.get(credential)


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[HostedToolCall] = []

    async def call(self, command: HostedToolCall) -> dict[str, object]:
        self.calls.append(command)
        return {"subject_id": str(command.principal.subject_id)}


def verified_credential(**changes: object) -> VerifiedCredential:
    value = VerifiedCredential(
        subject_id=UUID("20000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("20000000-0000-0000-0000-000000000002"),
        membership_id=UUID("20000000-0000-0000-0000-000000000003"),
        credential_id=UUID("20000000-0000-0000-0000-000000000004"),
        scopes=frozenset({"memory:read", "memory:write", "memory:delete"}),
        auth_method="oidc",
        issuer="https://issuer.example.test",
        audience="https://umcp.example.test/mcp",
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=5),
    )
    return replace(value, **changes)


def create_app(
    credentials: dict[str, VerifiedCredential | None],
) -> tuple[object, RecordingService]:
    service = RecordingService()
    app = create_local_hosted_gateway(
        service,
        SyntheticVerifier(credentials),
        issuer="https://issuer.example.test",
        audience="https://umcp.example.test/mcp",
        clock=lambda: NOW,
        request_id_factory=lambda: "req-hosted-gateway-test",
    )
    return app, service


def write_payload() -> dict[str, object]:
    return {
        "content": "The local gateway accepts only a verified principal.",
        "type": "lesson",
        "provenance": {"source_type": "conversation"},
        "idempotency_key": "hosted-gateway-test",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("authorization", "credentials", "status", "code"),
    [
        (None, {}, 401, "missing_credential"),
        ("Bearer revoked", {"revoked": None}, 401, "invalid_credential"),
        (
            "Bearer expired",
            {"expired": verified_credential(expires_at=NOW - timedelta(seconds=1))},
            401,
            "invalid_credential",
        ),
    ],
)
async def test_gateway_fails_closed_before_service_for_missing_or_invalid_credentials(
    authorization: str | None,
    credentials: dict[str, VerifiedCredential | None],
    status: int,
    code: str,
) -> None:
    app, service = create_app(credentials)
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
async def test_gateway_uses_only_verified_claims_for_tenant_and_principal() -> None:
    verified = verified_credential()
    app, service = create_app({"synthetic-verified": verified})
    payload = write_payload()
    payload.update({"tenant_id": "forged-tenant", "owner_id": "forged-owner"})
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        forged = await client.post(
            "/_hosted_boundary/memory.write",
            headers={"authorization": "Bearer synthetic-verified"},
            json=payload,
        )
        accepted = await client.post(
            "/_hosted_boundary/memory.write",
            headers={"authorization": "Bearer synthetic-verified"},
            json=write_payload(),
        )

    assert forged.status_code == 400
    assert forged.json() == {"ok": False, "error": {"code": "invalid_request"}}
    assert accepted.status_code == 200
    assert len(service.calls) == 1
    command = service.calls[0]
    assert command.principal.subject_id == verified.subject_id
    assert command.principal.tenant_id == verified.tenant_id
    assert command.principal.request_id == "req-hosted-gateway-test"
    assert "tenant_id" not in command.arguments
    assert "owner_id" not in command.arguments


def test_gateway_has_only_an_internal_boundary_route_not_a_hosted_mcp_endpoint() -> None:
    app, _ = create_app({})

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
    assert {route.path for route in app.routes} == {"/_hosted_boundary/{tool_name}"}
