"""Fail-closed, local-testable Cloud security ports and adapters.

These primitives deliberately do not claim an external OIDC/KMS integration.
They make the production boundary explicit while providing an isolated local
adapter for contract tests and development only.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from mcp.server.auth.provider import AccessToken


class Scope(StrEnum):
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    MEMORY_EXPORT = "memory:export"
    CONNECTIONS_MANAGE = "connections:manage"


@dataclass(frozen=True, slots=True)
class Principal:
    subject_id: UUID
    tenant_id: UUID
    membership_id: UUID
    scopes: frozenset[Scope]
    credential_id: UUID
    auth_method: str
    expires_at: datetime

    def requires(self, scope: Scope, *, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        if self.expires_at <= now or scope not in self.scopes:
            raise PermissionError("authorization denied")


class OIDCTokenVerifier(Protocol):
    """Production port implemented by a JWKS/OIDC verifier outside local dev."""

    async def verify_token(self, token: str) -> AccessToken | None: ...


class LocalDevelopmentTokenVerifier:
    """HMAC signed compact tokens for local tests only.

    The verifier checks issuer, audience/resource, expiry and a local
    revocation set. It deliberately accepts no unsigned token or client owner
    identifier, and has the same `verify_token` port as the official MCP SDK.
    """

    def __init__(self, *, secret: bytes, issuer: str, audience: str) -> None:
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._revoked: set[str] = set()

    def issue(
        self,
        *,
        subject: UUID,
        tenant_id: UUID,
        membership_id: UUID,
        credential_id: UUID,
        scopes: set[Scope],
        expires_at: datetime,
        client_id: str = "local-development",
    ) -> str:
        payload = {
            "aud": self._audience,
            "cid": client_id,
            "credential_id": str(credential_id),
            "exp": int(expires_at.timestamp()),
            "iss": self._issuer,
            "membership_id": str(membership_id),
            "scope": sorted(scope.value for scope in scopes),
            "sub": str(subject),
            "tenant_id": str(tenant_id),
        }
        encoded = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        signature = _b64(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
        return f"v1.{encoded}.{signature}"

    def revoke(self, token: str) -> None:
        self._revoked.add(hashlib.sha256(token.encode()).hexdigest())

    async def verify_token(self, token: str) -> AccessToken | None:
        if hashlib.sha256(token.encode()).hexdigest() in self._revoked:
            return None
        try:
            version, encoded, signature = token.split(".")
            expected = _b64(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
            payload = json.loads(_unb64(encoded))
            if (
                version != "v1"
                or not hmac.compare_digest(signature, expected)
                or payload["iss"] != self._issuer
                or payload["aud"] != self._audience
                or int(payload["exp"]) <= int(datetime.now(UTC).timestamp())
            ):
                return None
            UUID(payload["sub"])
            UUID(payload["tenant_id"])
            UUID(payload["membership_id"])
            UUID(payload["credential_id"])
            scopes = [Scope(item).value for item in payload["scope"]]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        return AccessToken(
            token=token,
            client_id=str(payload["cid"]),
            scopes=scopes,
            expires_at=int(payload["exp"]),
            resource=self._audience,
            subject=str(payload["sub"]),
            claims={
                "iss": self._issuer,
                "tenant_id": payload["tenant_id"],
                "membership_id": payload["membership_id"],
                "credential_id": payload["credential_id"],
            },
        )


def principal_from_access_token(token: AccessToken) -> Principal:
    claims = token.claims or {}
    try:
        return Principal(
            subject_id=UUID(str(token.subject)),
            tenant_id=UUID(str(claims["tenant_id"])),
            membership_id=UUID(str(claims["membership_id"])),
            credential_id=UUID(str(claims["credential_id"])),
            scopes=frozenset(Scope(item) for item in token.scopes),
            auth_method="local-development",
            expires_at=datetime.fromtimestamp(token.expires_at or 0, UTC),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise PermissionError("invalid principal claims") from exc


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class KeyManagementService(Protocol):
    def wrap(self, *, tenant_id: UUID, key_version: int, dek: bytes) -> bytes: ...

    def unwrap(self, *, tenant_id: UUID, key_version: int, wrapped_dek: bytes) -> bytes: ...


class KMSUnavailableError(PermissionError):
    """A hosted key service is unavailable; plaintext fallback is forbidden."""


class HostedKMSUnavailable:
    """Fail-closed seam for the future hosted KMS adapter.

    CP-3 explicitly blocks wiring a real provider in this package. Keeping the
    seam callable but unusable makes accidental hosted composition fail before
    any ciphertext is written or decrypted.
    """

    def __init__(self, reason: str = "hosted KMS adapter is not configured") -> None:
        self._reason = reason

    def wrap(self, *, tenant_id: UUID, key_version: int, dek: bytes) -> bytes:
        raise KMSUnavailableError(self._reason)

    def unwrap(self, *, tenant_id: UUID, key_version: int, wrapped_dek: bytes) -> bytes:
        raise KMSUnavailableError(self._reason)


class LocalDevelopmentKMS:
    """Process-local development KMS; never configure this in hosted staging/prod."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) not in (16, 24, 32):
            raise ValueError("master key must be an AES key")
        self._cipher = AESGCM(master_key)

    def _aad(self, tenant_id: UUID, key_version: int) -> bytes:
        return f"umcp/dek/v1/{tenant_id}/{key_version}".encode()

    def wrap(self, *, tenant_id: UUID, key_version: int, dek: bytes) -> bytes:
        if key_version < 1 or len(dek) != 32:
            raise KMSUnavailableError("invalid envelope key request")
        nonce = os.urandom(12)
        return nonce + self._cipher.encrypt(nonce, dek, self._aad(tenant_id, key_version))

    def unwrap(self, *, tenant_id: UUID, key_version: int, wrapped_dek: bytes) -> bytes:
        if key_version < 1 or len(wrapped_dek) < 12 + 16:
            raise KMSUnavailableError("key unwrap failed")
        try:
            dek = self._cipher.decrypt(
                wrapped_dek[:12], wrapped_dek[12:], self._aad(tenant_id, key_version)
            )
            if len(dek) != 32:
                raise ValueError("invalid DEK")
            return dek
        except Exception as exc:
            raise KMSUnavailableError("key unwrap failed") from exc


@dataclass(frozen=True, slots=True)
class EnvelopeCiphertext:
    key_version: int
    wrapped_dek: bytes
    nonce: bytes
    ciphertext: bytes

    def encode(self) -> str:
        value = {
            "v": 1,
            "k": self.key_version,
            "w": base64.urlsafe_b64encode(self.wrapped_dek).decode(),
            "n": base64.urlsafe_b64encode(self.nonce).decode(),
            "c": base64.urlsafe_b64encode(self.ciphertext).decode(),
        }
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @classmethod
    def decode(cls, value: str) -> EnvelopeCiphertext:
        """Parse the compact envelope persisted by Cloud repositories."""
        try:
            payload = json.loads(value)
            if (
                not isinstance(payload, dict)
                or payload["v"] != 1
                or not isinstance(payload["k"], int)
                or payload["k"] < 1
            ):
                raise ValueError("unsupported envelope")
            decoded = cls(
                key_version=payload["k"],
                wrapped_dek=base64.urlsafe_b64decode(str(payload["w"])),
                nonce=base64.urlsafe_b64decode(str(payload["n"])),
                ciphertext=base64.urlsafe_b64decode(str(payload["c"])),
            )
            if (
                len(decoded.wrapped_dek) < 12 + 16
                or len(decoded.nonce) != 12
                or len(decoded.ciphertext) < 16
            ):
                raise ValueError("invalid envelope lengths")
            return decoded
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeError,
            binascii.Error,
            json.JSONDecodeError,
        ) as exc:
            raise PermissionError("ciphertext envelope is invalid") from exc


class TenantEnvelopeEncryptor:
    def __init__(self, kms: KeyManagementService) -> None:
        self._kms = kms

    @staticmethod
    def _aad(*, tenant_id: UUID, record_id: UUID, field: str, key_version: int) -> bytes:
        return f"umcp/content/v1/{tenant_id}/{record_id}/{field}/{key_version}".encode()

    def encrypt(
        self, *, tenant_id: UUID, record_id: UUID, field: str, plaintext: str, key_version: int
    ) -> EnvelopeCiphertext:
        if key_version < 1 or not field or "/" in field:
            raise ValueError("invalid envelope field or key version")
        dek, nonce = os.urandom(32), os.urandom(12)
        ciphertext = AESGCM(dek).encrypt(
            nonce,
            plaintext.encode(),
            self._aad(
                tenant_id=tenant_id, record_id=record_id, field=field, key_version=key_version
            ),
        )
        try:
            wrapped_dek = self._kms.wrap(tenant_id=tenant_id, key_version=key_version, dek=dek)
        except Exception as exc:
            raise KMSUnavailableError("key wrap failed") from exc
        return EnvelopeCiphertext(key_version, wrapped_dek, nonce, ciphertext)

    def decrypt(
        self, *, tenant_id: UUID, record_id: UUID, field: str, value: EnvelopeCiphertext
    ) -> str:
        if value.key_version < 1 or len(value.nonce) != 12 or len(value.ciphertext) < 16:
            raise PermissionError("ciphertext envelope is invalid")
        try:
            dek = self._kms.unwrap(
                tenant_id=tenant_id, key_version=value.key_version, wrapped_dek=value.wrapped_dek
            )
        except Exception as exc:
            raise KMSUnavailableError("key unwrap failed") from exc
        if len(dek) != 32:
            raise KMSUnavailableError("key unwrap returned an invalid DEK")
        try:
            return (
                AESGCM(dek)
                .decrypt(
                    value.nonce,
                    value.ciphertext,
                    self._aad(
                        tenant_id=tenant_id,
                        record_id=record_id,
                        field=field,
                        key_version=value.key_version,
                    ),
                )
                .decode()
            )
        except Exception as exc:
            raise PermissionError("ciphertext authentication failed") from exc

    def rewrap(
        self,
        *,
        tenant_id: UUID,
        record_id: UUID,
        field: str,
        value: EnvelopeCiphertext,
        key_version: int,
    ) -> EnvelopeCiphertext:
        """Re-encrypt one field under a new version-bound AAD and wrapped DEK.

        The ciphertext AAD intentionally includes its key version, so a real
        rotation must authenticate/decrypt then encrypt again; merely swapping
        the wrapped DEK would make the record unreadable.
        """
        if key_version < 1:
            raise ValueError("key version must be positive")
        return self.encrypt(
            tenant_id=tenant_id,
            record_id=record_id,
            field=field,
            plaintext=self.decrypt(
                tenant_id=tenant_id, record_id=record_id, field=field, value=value
            ),
            key_version=key_version,
        )


@dataclass(frozen=True, slots=True)
class WorkerEnvelope:
    job_id: UUID
    tenant_id: UUID
    principal_id: UUID
    expires_at: datetime
    nonce: str
    signature: str

    def signing_input(self) -> bytes:
        fields = (
            "umcp.job.v1",
            str(self.job_id),
            str(self.tenant_id),
            str(self.principal_id),
            self.expires_at.isoformat(),
            self.nonce,
        )
        return "|".join(fields).encode()

    @classmethod
    def sign(
        cls,
        *,
        job_id: UUID,
        tenant_id: UUID,
        principal_id: UUID,
        expires_at: datetime,
        nonce: str,
        secret: bytes,
    ) -> WorkerEnvelope:
        unsigned = cls(job_id, tenant_id, principal_id, expires_at, nonce, "")
        signature = hmac.new(secret, unsigned.signing_input(), hashlib.sha256).hexdigest()
        return cls(job_id, tenant_id, principal_id, expires_at, nonce, signature)

    def verify(self, *, secret: bytes, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        expected = hmac.new(secret, self.signing_input(), hashlib.sha256).hexdigest()
        if (
            self.expires_at.tzinfo is None
            or not self.nonce
            or len(self.nonce) > 256
            or self.expires_at <= now
            or not hmac.compare_digest(expected, self.signature)
        ):
            raise PermissionError("worker envelope rejected")
