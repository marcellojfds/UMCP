"""Fail-closed, local-testable Cloud security ports and adapters.

These primitives deliberately do not claim an external OIDC/KMS integration.
They make the production boundary explicit while providing an isolated local
adapter for contract tests and development only.
"""

from __future__ import annotations

import base64
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


class KeyManagementService(Protocol):
    def wrap(self, *, tenant_id: UUID, key_version: int, dek: bytes) -> bytes: ...

    def unwrap(self, *, tenant_id: UUID, key_version: int, wrapped_dek: bytes) -> bytes: ...


class LocalDevelopmentKMS:
    """Process-local development KMS; never configure this in hosted staging/prod."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) not in (16, 24, 32):
            raise ValueError("master key must be an AES key")
        self._cipher = AESGCM(master_key)

    def _aad(self, tenant_id: UUID, key_version: int) -> bytes:
        return f"umcp/dek/v1/{tenant_id}/{key_version}".encode()

    def wrap(self, *, tenant_id: UUID, key_version: int, dek: bytes) -> bytes:
        nonce = os.urandom(12)
        return nonce + self._cipher.encrypt(nonce, dek, self._aad(tenant_id, key_version))

    def unwrap(self, *, tenant_id: UUID, key_version: int, wrapped_dek: bytes) -> bytes:
        if len(wrapped_dek) < 13:
            raise PermissionError("key unwrap failed")
        try:
            return self._cipher.decrypt(
                wrapped_dek[:12], wrapped_dek[12:], self._aad(tenant_id, key_version)
            )
        except Exception as exc:
            raise PermissionError("key unwrap failed") from exc


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


class TenantEnvelopeEncryptor:
    def __init__(self, kms: KeyManagementService) -> None:
        self._kms = kms

    @staticmethod
    def _aad(*, tenant_id: UUID, record_id: UUID, field: str, key_version: int) -> bytes:
        return f"umcp/content/v1/{tenant_id}/{record_id}/{field}/{key_version}".encode()

    def encrypt(
        self, *, tenant_id: UUID, record_id: UUID, field: str, plaintext: str, key_version: int
    ) -> EnvelopeCiphertext:
        dek, nonce = os.urandom(32), os.urandom(12)
        ciphertext = AESGCM(dek).encrypt(
            nonce,
            plaintext.encode(),
            self._aad(
                tenant_id=tenant_id, record_id=record_id, field=field, key_version=key_version
            ),
        )
        return EnvelopeCiphertext(
            key_version,
            self._kms.wrap(tenant_id=tenant_id, key_version=key_version, dek=dek),
            nonce,
            ciphertext,
        )

    def decrypt(
        self, *, tenant_id: UUID, record_id: UUID, field: str, value: EnvelopeCiphertext
    ) -> str:
        dek = self._kms.unwrap(
            tenant_id=tenant_id, key_version=value.key_version, wrapped_dek=value.wrapped_dek
        )
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
        if self.expires_at <= now or not hmac.compare_digest(expected, self.signature):
            raise PermissionError("worker envelope rejected")
