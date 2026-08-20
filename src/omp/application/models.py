"""Commands and results shared by transports and application services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from omp.domain import Memory, MemoryState, MemoryType, MemoryVersion, Provenance, Relation


@dataclass(frozen=True, slots=True)
class WriteMemoryCommand:
    owner_id: str
    content: str
    memory_type: MemoryType
    provenance: Provenance
    importance: float = 0.5
    confidence: float = 0.5
    space: str | None = None
    occurred_at: datetime | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class WriteMemoryResult:
    memory: Memory
    created: bool


@dataclass(frozen=True, slots=True)
class UpdateMemoryCommand:
    owner_id: str
    memory_id: UUID
    expected_version: int
    content: str | None = None
    memory_type: MemoryType | None = None
    importance: float | None = None
    confidence: float | None = None
    state: MemoryState | None = None
    occurred_at: datetime | None = None
    space: str | None = None
    provenance: Provenance | None = None
    supersedes_memory_id: UUID | None = None
    contradicts_memory_id: UUID | None = None
    change_reason: str = "updated"
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class ForgetMemoryCommand:
    owner_id: str
    memory_id: UUID
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class ForgetMemoryResult:
    memory_id: UUID
    forgotten: bool


@dataclass(frozen=True, slots=True)
class MemoryExportRecord:
    """Owner-scoped administrative export record.

    The vector is opt-in and absent from the default export. The write
    fingerprint is metadata required to preserve write-key replay semantics;
    operation-ledger rows are intentionally never part of this DTO.
    """

    memory: Memory
    history: tuple[MemoryVersion, ...]
    relations: tuple[Relation, ...]
    embedding: tuple[float, ...] | None = None
    write_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class MemoryImportRecord:
    memory: Memory
    history: tuple[MemoryVersion, ...]
    relations: tuple[Relation, ...]
    embedding: tuple[float, ...] | None = None
    write_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class ImportResult:
    imported: int
    replayed: int


@dataclass(frozen=True, slots=True)
class SearchFilters:
    states: frozenset[MemoryState] = field(default_factory=lambda: frozenset({MemoryState.ACTIVE}))
    memory_types: frozenset[MemoryType] | None = None
    space: str | None = None
    min_importance: float | None = None
    min_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class SearchMemoryCommand:
    owner_id: str
    query: str
    filters: SearchFilters = field(default_factory=SearchFilters)
    limit: int = 5
    candidate_limit: int = 50
    threshold: float = 0.78


@dataclass(frozen=True, slots=True)
class SearchMemoryItem:
    memory: Memory
    score: float
    similarity: float
    profile_id: str
    profile_version: str
    reason_retrieved: str


@dataclass(frozen=True, slots=True)
class SearchMemoryResult:
    items: tuple[SearchMemoryItem, ...]
    profile_id: str
    profile_version: str


@dataclass(frozen=True, slots=True)
class RelateMemoriesCommand:
    owner_id: str
    source_memory_id: UUID
    target_memory_id: UUID
    relation_type: str


@dataclass(frozen=True, slots=True)
class RelateMemoriesResult:
    relation: Relation
