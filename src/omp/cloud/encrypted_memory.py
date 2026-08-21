"""Local Cloud memory adapter that persists only envelope ciphertext fields."""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from .security import EnvelopeCiphertext, TenantEnvelopeEncryptor


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class EncryptedCloudMemoryService:
    """A local/dev Cloud adapter; never stores content/provenance in plaintext.

    Vectors are deliberately out of scope for this adapter: production pgvector
    remains protected by RLS/storage encryption, as documented in ADR 0013.
    """

    def __init__(self, encryptor: TenantEnvelopeEncryptor, *, key_version: int = 1) -> None:
        self._encryptor = encryptor
        self._key_version = key_version
        self._records: dict[str, dict[str, Any]] = {}
        self._write_keys: dict[tuple[str, str], str] = {}
        self._forget_keys: set[tuple[str, str]] = set()
        self._tombstones: dict[tuple[str, str], str] = {}

    @staticmethod
    def _tenant(owner_id: str) -> UUID:
        try:
            prefix, tenant, _ = owner_id.split(":", 2)
            if prefix != "cloud":
                raise ValueError
            return UUID(tenant)
        except ValueError as exc:
            raise PermissionError("Cloud owner binding is invalid") from exc

    @staticmethod
    def _cipher(value: EnvelopeCiphertext) -> dict[str, Any]:
        return {
            "key_version": value.key_version,
            "wrapped_dek": value.wrapped_dek,
            "nonce": value.nonce,
            "ciphertext": value.ciphertext,
        }

    @staticmethod
    def _uncipher(value: dict[str, Any]) -> EnvelopeCiphertext:
        return EnvelopeCiphertext(**value)

    def _read(self, stored: dict[str, Any]) -> dict[str, Any]:
        tenant, record_id = self._tenant(stored["owner_id"]), UUID(stored["id"][4:])
        content = self._encryptor.decrypt(
            tenant_id=tenant,
            record_id=record_id,
            field="content",
            value=self._uncipher(stored["content_ciphertext"]),
        )
        provenance = json.loads(
            self._encryptor.decrypt(
                tenant_id=tenant,
                record_id=record_id,
                field="provenance",
                value=self._uncipher(stored["provenance_ciphertext"]),
            )
        )
        return {
            key: value
            for key, value in stored.items()
            if key not in {"content_ciphertext", "provenance_ciphertext"}
        } | {"content": content, "provenance": provenance}

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        owner, key = str(payload["owner_id"]), str(payload["idempotency_key"])
        tenant = self._tenant(owner)
        existing = self._write_keys.get((owner, key))
        if existing:
            return {"memory": self._read(self._records[existing]), "status": "already_exists"}
        memory_id, now = "mem_" + uuid.uuid4().hex, _now()
        record_id = UUID(hex=memory_id[4:])
        stored = {
            "id": memory_id,
            "owner_id": owner,
            "type": payload["type"],
            "space": payload.get("space"),
            "importance": payload.get("importance", 0.5),
            "confidence": payload.get("confidence", 0.5),
            "state": "active",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "occurred_at": None,
            "content_ciphertext": self._cipher(
                self._encryptor.encrypt(
                    tenant_id=tenant,
                    record_id=record_id,
                    field="content",
                    plaintext=str(payload["content"]),
                    key_version=self._key_version,
                )
            ),
            "provenance_ciphertext": self._cipher(
                self._encryptor.encrypt(
                    tenant_id=tenant,
                    record_id=record_id,
                    field="provenance",
                    plaintext=json.dumps(payload["provenance"], sort_keys=True),
                    key_version=self._key_version,
                )
            ),
        }
        self._records[memory_id] = stored
        self._write_keys[(owner, key)] = memory_id
        return {"memory": self._read(stored), "status": "created"}

    def search(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        owner, query = (
            str(payload["owner_id"]),
            set(re.findall(r"[\wÀ-ÿ]+", str(payload["query"]).casefold())),
        )
        self._tenant(owner)
        output: list[dict[str, Any]] = []
        for stored in self._records.values():
            if stored["owner_id"] != owner or stored["state"] != payload.get("state", "active"):
                continue
            record = self._read(stored)
            if query & set(re.findall(r"[\wÀ-ÿ]+", record["content"].casefold())):
                output.append({"memory": record, "score": 0.9})
        return output[: int(payload.get("limit", 10))]

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        stored = self._records.get(str(payload["id"]))
        if stored is None or stored["owner_id"] != payload["owner_id"]:
            raise KeyError("not found")
        if stored["version"] != payload["expected_version"]:
            raise ValueError("version conflict")
        record_id, tenant = UUID(stored["id"][4:]), self._tenant(stored["owner_id"])
        patch = payload["patch"]
        if patch.get("content") is not None:
            stored["content_ciphertext"] = self._cipher(
                self._encryptor.encrypt(
                    tenant_id=tenant,
                    record_id=record_id,
                    field="content",
                    plaintext=str(patch["content"]),
                    key_version=self._key_version,
                )
            )
        for key in ("type", "space", "importance", "confidence", "state"):
            if patch.get(key) is not None:
                stored[key] = patch[key]
        stored["version"] += 1
        stored["updated_at"] = _now()
        return {"memory": self._read(stored), "status": "updated"}

    def forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = (str(payload["owner_id"]), str(payload["id"]))
        if key in self._forget_keys:
            return {"status": "already_absent"}
        self._forget_keys.add(key)
        record = self._records.get(key[1])
        if record is None or record["owner_id"] != key[0]:
            return {"status": "already_absent"}
        # This is intentionally content-free and survives a logical backup
        # replay. A restored record is removed before it can become readable.
        self._tombstones[key] = _now()
        del self._records[key[1]]
        return {"status": "forgotten"}

    def delete_owner(self, owner_id: str) -> int:
        """Apply a local account deletion without retaining deleted payloads.

        Production account deletion is an asynchronous, externally provisioned
        workflow. The local Cloud adapter performs the equivalent owner-scoped
        operation synchronously so its Admin API contract is executable.
        """
        self._tenant(owner_id)
        memory_ids = [
            memory_id
            for memory_id, record in self._records.items()
            if record["owner_id"] == owner_id
        ]
        for memory_id in memory_ids:
            self._forget_keys.add((owner_id, memory_id))
            self._tombstones[(owner_id, memory_id)] = _now()
            del self._records[memory_id]
        self._write_keys = {
            key: memory_id
            for key, memory_id in self._write_keys.items()
            if key[0] != owner_id
        }
        return len(memory_ids)

    def tombstones(self) -> tuple[dict[str, str], ...]:
        """Return the content-free deletion ledger for an external restore job."""
        return tuple(
            {"owner_id": owner, "memory_id": memory_id, "deleted_at": deleted_at}
            for (owner, memory_id), deleted_at in sorted(self._tombstones.items())
        )

    def backup(self) -> dict[str, object]:
        """Create a logical local-dev snapshot containing ciphertext only."""
        return {"records": deepcopy(self._records), "tombstones": self.tombstones()}

    def restore(
        self, snapshot: dict[str, object], *, tombstones: tuple[dict[str, str], ...] = ()
    ) -> int:
        """Restore ciphertext then reapply deletion ledger before exposing records."""
        records = snapshot.get("records")
        if not isinstance(records, dict):
            raise ValueError("invalid backup snapshot")
        ledger = (*self.tombstones(), *tombstones)
        for entry in ledger:
            owner, memory_id, deleted_at = (
                entry.get("owner_id"),
                entry.get("memory_id"),
                entry.get("deleted_at"),
            )
            if (
                not isinstance(owner, str)
                or not isinstance(memory_id, str)
                or not isinstance(deleted_at, str)
            ):
                raise ValueError("invalid deletion tombstone")
            self._tombstones[(owner, memory_id)] = deleted_at
        restored = deepcopy(records)
        for owner, memory_id in self._tombstones:
            candidate = restored.get(memory_id)
            if isinstance(candidate, dict) and candidate.get("owner_id") == owner:
                restored.pop(memory_id, None)
        self._records = restored
        replayed_keys: dict[tuple[str, str], str] = {}
        for (owner, key), memory_id in self._write_keys.items():
            record = self._records.get(memory_id)
            if record is not None and str(record["owner_id"]) == owner:
                replayed_keys[(owner, key)] = memory_id
        self._write_keys = replayed_keys
        return len(self._records)

    def rotate(self, version: int) -> None:
        if version < 1:
            raise ValueError("key version must be positive")
        self._key_version = version

    def rewrap(self, version: int) -> int:
        """Rotate existing encrypted fields without retaining plaintext in storage."""
        if version < 1:
            raise ValueError("key version must be positive")
        migrated = 0
        for stored in self._records.values():
            tenant, record_id = self._tenant(stored["owner_id"]), UUID(stored["id"][4:])
            for field in ("content", "provenance"):
                ciphertext_key = f"{field}_ciphertext"
                current = self._uncipher(stored[ciphertext_key])
                if current.key_version == version:
                    continue
                stored[ciphertext_key] = self._cipher(
                    self._encryptor.rewrap(
                        tenant_id=tenant,
                        record_id=record_id,
                        field=field,
                        value=current,
                        key_version=version,
                    )
                )
                migrated += 1
        self._key_version = version
        return migrated

    def raw_dump(self) -> str:
        return repr(self._records)
