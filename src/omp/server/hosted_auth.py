"""Fail-closed authentication boundary for a future hosted composition.

This module intentionally has no identity-provider implementation.  A hosted
runtime must supply a verifier that has already checked the credential's
signature/JWKS, revocation and client binding.  The boundary then validates
the claims that bind that verified credential to UMCP and creates the only
principal accepted by the hosted adapter.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID


class HostedAuthenticationError(PermissionError):
    """A safe authorization failure that never includes credential material."""

    def __init__(self, code: str, *, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class VerifiedCredential:
    """Claims returned only by an injected, signature-verifying credential port."""

    subject_id: UUID
    tenant_id: UUID
    membership_id: UUID
    credential_id: UUID
    scopes: frozenset[str]
    auth_method: Literal["oidc", "pat"]
    issuer: str
    audience: str
    issued_at: datetime
    expires_at: datetime
    not_before: datetime | None = None
    consent_id: UUID | None = None


class CredentialVerifier(Protocol):
    """Verifier port; implementations must never return unverified claims."""

    def verify(self, credential: str) -> VerifiedCredential | None: ...


@dataclass(frozen=True, slots=True)
class Principal:
    """Immutable hosted identity derived exclusively from verified claims."""

    subject_id: UUID
    tenant_id: UUID
    membership_id: UUID
    scopes: frozenset[str]
    auth_method: Literal["oidc", "pat"]
    credential_id: UUID
    issued_at: datetime
    expires_at: datetime
    consent_id: UUID | None
    request_id: str


class HostedAuthenticator:
    """Convert a verified bearer credential into a constrained ``Principal``."""

    def __init__(
        self,
        verifier: CredentialVerifier,
        *,
        issuer: str,
        audience: str,
        clock: Callable[[], datetime] | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not issuer or not audience:
            raise ValueError("hosted issuer and audience are required")
        self._verifier = verifier
        self._issuer = issuer
        self._audience = audience
        self._clock = clock or (lambda: datetime.now(UTC))
        self._request_id_factory = request_id_factory or (lambda: "req_" + uuid.uuid4().hex)

    async def authenticate(self, authorization: str | None, *, required_scope: str) -> Principal:
        credential = self._bearer_credential(authorization)
        try:
            verified = self._verifier.verify(credential)
            if inspect.isawaitable(verified):
                verified = await verified
        except Exception as exc:
            raise HostedAuthenticationError("invalid_credential", status_code=401) from exc
        if verified is None or not isinstance(verified, VerifiedCredential):
            raise HostedAuthenticationError("invalid_credential", status_code=401)
        return self._principal_from_verified(verified, required_scope=required_scope)

    @staticmethod
    def _bearer_credential(authorization: str | None) -> str:
        if not isinstance(authorization, str):
            raise HostedAuthenticationError("missing_credential", status_code=401)
        scheme, separator, credential = authorization.partition(" ")
        if (
            scheme.lower() != "bearer"
            or not separator
            or not credential
            or credential.strip() != credential
        ):
            raise HostedAuthenticationError("invalid_credential", status_code=401)
        return credential

    def _principal_from_verified(
        self, verified: VerifiedCredential, *, required_scope: str
    ) -> Principal:
        now = _aware_utc(self._clock())
        try:
            issued_at = _aware_utc(verified.issued_at)
            expires_at = _aware_utc(verified.expires_at)
            not_before = _aware_utc(verified.not_before) if verified.not_before else None
        except (AttributeError, TypeError, ValueError) as exc:
            raise HostedAuthenticationError("invalid_credential", status_code=401) from exc
        if (
            verified.issuer != self._issuer
            or verified.audience != self._audience
            or expires_at <= now
            or issued_at > now
            or issued_at >= expires_at
            or (not_before is not None and not_before > now)
        ):
            raise HostedAuthenticationError("invalid_credential", status_code=401)
        if (
            not all(
                isinstance(value, UUID)
                for value in (
                    verified.subject_id,
                    verified.tenant_id,
                    verified.membership_id,
                    verified.credential_id,
                )
            )
            or (verified.consent_id is not None and not isinstance(verified.consent_id, UUID))
            or verified.auth_method not in {"oidc", "pat"}
            or not all(isinstance(scope, str) and scope for scope in verified.scopes)
        ):
            raise HostedAuthenticationError("invalid_credential", status_code=401)
        if required_scope not in verified.scopes:
            raise HostedAuthenticationError("insufficient_scope", status_code=403)
        return Principal(
            subject_id=verified.subject_id,
            tenant_id=verified.tenant_id,
            membership_id=verified.membership_id,
            scopes=frozenset(verified.scopes),
            auth_method=verified.auth_method,
            credential_id=verified.credential_id,
            issued_at=issued_at,
            expires_at=expires_at,
            consent_id=verified.consent_id,
            request_id=self._request_id_factory(),
        )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("credential timestamps must be timezone-aware")
    return value.astimezone(UTC)


__all__ = [
    "CredentialVerifier",
    "HostedAuthenticationError",
    "HostedAuthenticator",
    "Principal",
    "VerifiedCredential",
]
