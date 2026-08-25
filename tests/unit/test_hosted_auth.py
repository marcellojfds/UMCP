from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from omp.server.hosted_auth import (
    HostedAuthenticationError,
    HostedAuthenticator,
    VerifiedCredential,
)

NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)


class SyntheticVerifier:
    """A verifier test double, not a token parser or signing implementation."""

    def __init__(self, credentials: dict[str, VerifiedCredential | None]) -> None:
        self.credentials = credentials

    def verify(self, credential: str) -> VerifiedCredential | None:
        return self.credentials.get(credential)


def credential(**changes: object) -> VerifiedCredential:
    value = VerifiedCredential(
        subject_id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000002"),
        membership_id=UUID("00000000-0000-0000-0000-000000000003"),
        credential_id=UUID("00000000-0000-0000-0000-000000000004"),
        scopes=frozenset({"memory:read", "memory:write", "memory:delete"}),
        auth_method="oidc",
        issuer="https://issuer.example.test",
        audience="https://umcp.example.test/mcp",
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(minutes=5),
        not_before=NOW - timedelta(minutes=1),
    )
    return replace(value, **changes)


def authenticator(values: dict[str, VerifiedCredential | None]) -> HostedAuthenticator:
    return HostedAuthenticator(
        SyntheticVerifier(values),
        issuer="https://issuer.example.test",
        audience="https://umcp.example.test/mcp",
        clock=lambda: NOW,
        request_id_factory=lambda: "req-hosted-test",
    )


@pytest.mark.asyncio
async def test_authenticator_builds_an_immutable_principal_from_verified_claims() -> None:
    principal = await authenticator({"synthetic-verified": credential()}).authenticate(
        "Bearer synthetic-verified", required_scope="memory:write"
    )

    assert principal.subject_id == UUID("00000000-0000-0000-0000-000000000001")
    assert principal.tenant_id == UUID("00000000-0000-0000-0000-000000000002")
    assert principal.request_id == "req-hosted-test"
    with pytest.raises(FrozenInstanceError):
        principal.tenant_id = UUID("00000000-0000-0000-0000-000000000099")  # type: ignore[misc]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("authorization", "verified", "required_scope", "status", "code"),
    [
        (None, None, "memory:write", 401, "missing_credential"),
        ("Basic synthetic", None, "memory:write", 401, "invalid_credential"),
        ("Bearer malformed", None, "memory:write", 401, "invalid_credential"),
        (
            "Bearer expired",
            credential(expires_at=NOW - timedelta(seconds=1)),
            "memory:write",
            401,
            "invalid_credential",
        ),
        (
            "Bearer wrong-issuer",
            credential(issuer="https://other.example.test"),
            "memory:write",
            401,
            "invalid_credential",
        ),
        (
            "Bearer wrong-audience",
            credential(audience="https://other.example.test/mcp"),
            "memory:write",
            401,
            "invalid_credential",
        ),
        (
            "Bearer missing-scope",
            credential(scopes=frozenset({"memory:read"})),
            "memory:write",
            403,
            "insufficient_scope",
        ),
    ],
)
async def test_authenticator_fails_closed_for_invalid_or_insufficient_credentials(
    authorization: str | None,
    verified: VerifiedCredential | None,
    required_scope: str,
    status: int,
    code: str,
) -> None:
    value = authenticator(
        {
            "expired": verified,
            "wrong-issuer": verified,
            "wrong-audience": verified,
            "missing-scope": verified,
        }
    )

    with pytest.raises(HostedAuthenticationError) as raised:
        await value.authenticate(authorization, required_scope=required_scope)

    assert raised.value.status_code == status
    assert raised.value.code == code
