"""Memory aggregate and its lifecycle invariants."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Final
from uuid import UUID, uuid4

from .errors import InvalidStateTransitionError, ValidationError
from .types import (
    EmbeddingDescriptor,
    MemoryState,
    MemoryType,
    Provenance,
    ensure_aware,
    utc_now,
    validate_idempotency_key,
    validate_owner_id,
    validate_space,
    validate_unit_interval,
)

_UNSET: Final = object()


@dataclass(frozen=True, slots=True)
class MemoryVersion:
    """Immutable snapshot kept for audit/history until the memory is forgotten."""

    memory_id: UUID
    version: int
    content: str
    memory_type: MemoryType
    state: MemoryState
    importance: float
    confidence: float
    space: str | None
    occurred_at: datetime | None
    provenance: Provenance
    changed_at: datetime
    change_reason: str


@dataclass(frozen=True, slots=True)
class Memory:
    id: UUID
    owner_id: str
    content: str
    memory_type: MemoryType
    importance: float
    confidence: float
    state: MemoryState
    version: int
    created_at: datetime
    updated_at: datetime
    occurred_at: datetime | None
    space: str | None
    provenance: Provenance
    embedding: EmbeddingDescriptor | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        validate_owner_id(self.owner_id)
        if not isinstance(self.id, UUID):
            raise ValidationError("memory id must be a UUID")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValidationError("content must be non-empty")
        if len(self.content) > 100_000:
            raise ValidationError("content exceeds the maximum length")
        validate_unit_interval(self.importance, "importance")
        validate_unit_interval(self.confidence, "confidence")
        if self.version < 1:
            raise ValidationError("version must be positive")
        created_at = ensure_aware(self.created_at, "created_at")
        updated_at = ensure_aware(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValidationError("updated_at cannot precede created_at")
        if self.occurred_at is not None:
            ensure_aware(self.occurred_at, "occurred_at")
        validate_space(self.space)
        validate_idempotency_key(self.idempotency_key)
        if self.state not in MemoryState:
            raise ValidationError("unknown memory state")

    @classmethod
    def create(
        cls,
        *,
        owner_id: str,
        content: str,
        memory_type: MemoryType,
        importance: float,
        confidence: float,
        provenance: Provenance,
        space: str | None = None,
        occurred_at: datetime | None = None,
        embedding: EmbeddingDescriptor | None = None,
        idempotency_key: str | None = None,
        memory_id: UUID | None = None,
        now: datetime | None = None,
    ) -> Memory:
        timestamp = utc_now() if now is None else ensure_aware(now, "now")
        return cls(
            id=memory_id or uuid4(),
            owner_id=owner_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            confidence=confidence,
            state=MemoryState.ACTIVE,
            version=1,
            created_at=timestamp,
            updated_at=timestamp,
            occurred_at=occurred_at,
            space=space,
            provenance=provenance,
            embedding=embedding,
            idempotency_key=idempotency_key,
        )

    def snapshot(self, *, change_reason: str) -> MemoryVersion:
        return MemoryVersion(
            memory_id=self.id,
            version=self.version,
            content=self.content,
            memory_type=self.memory_type,
            state=self.state,
            importance=self.importance,
            confidence=self.confidence,
            space=self.space,
            occurred_at=self.occurred_at,
            provenance=self.provenance,
            changed_at=self.updated_at,
            change_reason=change_reason,
        )

    def evolve(
        self,
        *,
        now: datetime,
        content: str | object = _UNSET,
        memory_type: MemoryType | object = _UNSET,
        importance: float | object = _UNSET,
        confidence: float | object = _UNSET,
        state: MemoryState | object = _UNSET,
        occurred_at: datetime | None | object = _UNSET,
        space: str | None | object = _UNSET,
        provenance: Provenance | object = _UNSET,
        embedding: EmbeddingDescriptor | None | object = _UNSET,
        change_reason: str = "updated",
        related_memory_id: UUID | None = None,
    ) -> Memory:
        next_state = self.state if state is _UNSET else state
        if not isinstance(next_state, MemoryState):
            raise ValidationError("state must be a valid MemoryState")
        self._assert_transition(next_state, related_memory_id)
        if not change_reason.strip():
            raise ValidationError("change_reason must be non-empty")
        values: dict[str, Any] = {
            "content": self.content if content is _UNSET else content,
            "memory_type": self.memory_type if memory_type is _UNSET else memory_type,
            "importance": self.importance if importance is _UNSET else importance,
            "confidence": self.confidence if confidence is _UNSET else confidence,
            "state": next_state,
            "occurred_at": self.occurred_at if occurred_at is _UNSET else occurred_at,
            "space": self.space if space is _UNSET else space,
            "provenance": self.provenance if provenance is _UNSET else provenance,
            "embedding": self.embedding if embedding is _UNSET else embedding,
            "version": self.version + 1,
            "updated_at": ensure_aware(now, "now"),
        }
        return replace(self, **values)

    def _assert_transition(self, target: MemoryState, related_memory_id: UUID | None) -> None:
        if target == self.state == MemoryState.ACTIVE:
            return
        allowed: dict[MemoryState, set[MemoryState]] = {
            MemoryState.ACTIVE: {
                MemoryState.ACTIVE,
                MemoryState.SUPERSEDED,
                MemoryState.CONTRADICTED,
                MemoryState.ARCHIVED,
            },
            MemoryState.CONTRADICTED: {MemoryState.ACTIVE},
            MemoryState.ARCHIVED: {MemoryState.ACTIVE},
            MemoryState.SUPERSEDED: set(),
        }
        if target not in allowed[self.state]:
            raise InvalidStateTransitionError(
                f"cannot transition memory from {self.state.value} to {target.value}"
            )
        if (
            target in {MemoryState.SUPERSEDED, MemoryState.CONTRADICTED}
            and related_memory_id is None
        ):
            raise InvalidStateTransitionError(
                f"transition to {target.value} requires a related memory id"
            )
