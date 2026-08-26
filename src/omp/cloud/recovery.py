"""Local recovery contracts and evidence for the hosted boundary.

This module intentionally contains no backup transport, PITR client, cloud
credential or provider SDK.  The hosted adapter is an explicit fail-closed
interface; the local fixture measures only a disposable ciphertext snapshot
restore into a caller-provided isolated service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Protocol, cast
from uuid import uuid4


class RecoveryUnavailableError(PermissionError):
    """Hosted backup/PITR is not configured in the local package."""


class HostedRecoveryAdapter:
    """Fail-closed seam for a future hosted backup/PITR implementation."""

    def __init__(self, reason: str = "hosted recovery adapter is not configured") -> None:
        self._reason = reason

    def inventory(self) -> tuple[RecoveryInventory, ...]:
        raise RecoveryUnavailableError(self._reason)

    def restore_isolated(self, *, backup_id: str) -> RecoveryReceipt:
        raise RecoveryUnavailableError(self._reason)


@dataclass(frozen=True, slots=True)
class RecoveryInventory:
    """Content-free inventory metadata required for an auditable backup."""

    backup_id: str
    captured_at: datetime
    migration_head: str
    encrypted_payloads: bool
    tombstones_included: bool
    source: str = "local-fixture"

    def __post_init__(self) -> None:
        if not self.backup_id or not self.migration_head:
            raise ValueError("backup inventory identifiers are required")
        if self.captured_at.tzinfo is None:
            raise ValueError("backup inventory timestamp must be timezone-aware")
        if not self.encrypted_payloads or not self.tombstones_included:
            raise ValueError("recovery inventory must include ciphertext and tombstones")


@dataclass(frozen=True, slots=True)
class RecoveryReceipt:
    """Measured result of one local isolated restore attempt."""

    backup_id: str
    target: str
    restored_records: int
    tombstones_replayed: int
    rpo_seconds: float
    rto_seconds: float
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.target != "isolated":
            raise ValueError("recovery target must be isolated")
        if self.restored_records < 0 or self.tombstones_replayed < 0:
            raise ValueError("recovery counts cannot be negative")
        if self.rpo_seconds < 0 or self.rto_seconds < 0:
            raise ValueError("recovery timings cannot be negative")


class LocalSnapshotService(Protocol):
    def backup(self) -> dict[str, object]: ...

    def restore(
        self, snapshot: dict[str, object], *, tombstones: tuple[dict[str, str], ...] = ()
    ) -> int: ...

    def tombstones(self) -> tuple[dict[str, str], ...]: ...


class LocalRecoveryFixture:
    """Inventory and restore helper for disposable local encrypted services."""

    def __init__(self, *, migration_head: str) -> None:
        self._migration_head = migration_head

    def backup(self, service: LocalSnapshotService) -> tuple[dict[str, object], RecoveryInventory]:
        captured_at = datetime.now(UTC)
        snapshot = service.backup()
        records = snapshot.get("records")
        tombstones = snapshot.get("tombstones")
        if not isinstance(records, dict) or not isinstance(tombstones, tuple):
            raise ValueError("local backup is not an encrypted, inventoried snapshot")
        backup_id = str(uuid4())
        inventory = RecoveryInventory(
            backup_id=backup_id,
            captured_at=captured_at,
            migration_head=self._migration_head,
            encrypted_payloads=True,
            tombstones_included=True,
        )
        return snapshot, inventory

    def restore_isolated(
        self,
        service: LocalSnapshotService,
        snapshot: dict[str, object],
        inventory: RecoveryInventory,
        *,
        tombstones: tuple[dict[str, str], ...] = (),
    ) -> RecoveryReceipt:
        started = monotonic()
        now = datetime.now(UTC)
        if inventory.source != "local-fixture":
            raise RecoveryUnavailableError("foreign backup source is not accepted locally")
        if snapshot.get("format") != "omp.cloud.backup.v1":
            raise ValueError("unsupported local backup format")
        raw_ledger = snapshot.get("tombstones", ())
        if not isinstance(raw_ledger, tuple) or not all(
            isinstance(item, dict) for item in raw_ledger
        ):
            raise ValueError("backup tombstone ledger is invalid")
        ledger = cast(tuple[dict[str, str], ...], raw_ledger) + tombstones
        restored = service.restore(snapshot, tombstones=ledger)
        return RecoveryReceipt(
            backup_id=inventory.backup_id,
            target="isolated",
            restored_records=restored,
            tombstones_replayed=len(ledger),
            rpo_seconds=max(0.0, (now - inventory.captured_at).total_seconds()),
            rto_seconds=max(0.0, monotonic() - started),
            observed_at=now,
        )
