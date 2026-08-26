"""Local-only OAuth/OIDC contracts and fail-closed synthetic flows.

The module defines boundaries for a future provider adapter.  It deliberately
does not issue, parse, sign, or persist real credentials and contains no
provider or client registration data.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from .hosted_auth import VerifiedCredential


class IdentityContractError(PermissionError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProtectedResourceMetadata:
    resource: str
    authorization_servers: tuple[str, ...]
    scopes_supported: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AuthorizationServerMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    code_challenge_methods_supported: tuple[str, ...] = ("S256",)


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    client_id: str
    redirect_uri: str
    scope: frozenset[str]
    state: str
    code_challenge: str
    code_challenge_method: str = "S256"


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    consent_id: UUID
    subject_id: UUID
    client_id: str
    scopes: frozenset[str]
    policy_version: str
    version: int
    granted_at: datetime
    connection_id: UUID


@dataclass(frozen=True, slots=True)
class RevocationEvent:
    credential_id: UUID
    connection_id: UUID
    revoked_at: datetime
    reason: str


class IdentityProviderAdapter(Protocol):
    def exchange_code(self, code: str, *, code_verifier: str) -> VerifiedCredential: ...


class SyntheticIdentityFlow:
    """Deterministic in-process flow used only by contract tests."""

    def __init__(self, *, allowed_redirect_uris: frozenset[str], now: datetime) -> None:
        self._allowed_redirect_uris = allowed_redirect_uris
        self._now = now
        self._codes: dict[str, tuple[AuthorizationRequest, str]] = {}
        self._consents: dict[UUID, ConsentRecord] = {}
        self._revoked_credentials: set[UUID] = set()
        self._revoked_connections: set[UUID] = set()

    def authorize(self, request: AuthorizationRequest, *, consent: ConsentRecord) -> str:
        if request.redirect_uri not in self._allowed_redirect_uris:
            raise IdentityContractError("invalid_redirect_uri")
        if request.code_challenge_method != "S256" or not request.code_challenge:
            raise IdentityContractError("pkce_required")
        if request.scope != consent.scopes or request.client_id != consent.client_id:
            raise IdentityContractError("consent_mismatch")
        self._consents[consent.consent_id] = consent
        code = "synthetic-code-" + secrets.token_hex(8)
        self._codes[code] = (request, str(consent.consent_id))
        return code

    def redeem_code(self, code: str, *, code_verifier: str) -> ConsentRecord:
        entry = self._codes.pop(code, None)
        if entry is None:
            raise IdentityContractError("invalid_or_reused_code")
        request, consent_id = entry
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        if not hmac.compare_digest(expected, request.code_challenge):
            raise IdentityContractError("pkce_verification_failed")
        return self._consents[UUID(consent_id)]

    def revoke(self, *, credential_id: UUID, connection_id: UUID, reason: str) -> RevocationEvent:
        self._revoked_credentials.add(credential_id)
        self._revoked_connections.add(connection_id)
        return RevocationEvent(credential_id, connection_id, self._now, reason)

    def is_revoked(self, *, credential_id: UUID, connection_id: UUID) -> bool:
        return (
            credential_id in self._revoked_credentials
            or connection_id in self._revoked_connections
        )

    @staticmethod
    def consent(
        *, subject_id: UUID, client_id: str, scopes: frozenset[str], connection_id: UUID
    ) -> ConsentRecord:
        return ConsentRecord(
            uuid4(), subject_id, client_id, scopes, "synthetic-policy-v1", 1,
            datetime.now(UTC), connection_id
        )


__all__ = [
    "AuthorizationRequest", "AuthorizationServerMetadata", "ConsentRecord",
    "IdentityContractError", "IdentityProviderAdapter", "ProtectedResourceMetadata",
    "RevocationEvent", "SyntheticIdentityFlow",
]
