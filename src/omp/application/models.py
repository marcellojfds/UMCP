"""Commands and results shared by transports and application services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from omp.domain import (
    CaptureConsent,
    Memory,
    MemoryState,
    MemoryType,
    MemoryVersion,
    Provenance,
    Relation,
)


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
    tenant_id: str | None = None


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
    reason_code: str = "user_requested_memory"
    tenant_id: str | None = None


@dataclass(frozen=True, slots=True)
class ForgetMemoryResult:
    memory_id: UUID
    forgotten: bool


@dataclass(frozen=True, slots=True)
class SpacePolicy:
    default_recall: str = "same_space_only"
    allowed_spaces: frozenset[str] = frozenset()
    allow_global: bool = False
    allow_mental_notes_cross_space: bool = False

    def allows(self, space: str | None, *, context_space: str | None) -> bool:
        if space == context_space:
            return True
        if space is None and self.allow_global:
            return True
        return self.default_recall == "explicit_allowlist" and space in self.allowed_spaces


@dataclass(frozen=True, slots=True)
class CaptureMemoryCommand:
    tenant_id: str
    owner_id: str
    connection_id: str
    content: str
    memory_type: MemoryType
    space: str | None
    provenance: Provenance
    consent: CaptureConsent
    idempotency_key: str
    importance: float = 0.5
    confidence: float = 0.5
    capture_policy: str = "assisted"
    connection_revoked: bool = False
    scopes: frozenset[str] = frozenset({"memory:write"})


@dataclass(frozen=True, slots=True)
class CaptureMemoryResult:
    memory: Memory
    created: bool


@dataclass(frozen=True, slots=True)
class ListInboxCommand:
    tenant_id: str
    owner_id: str
    connection_id: str
    space: str | None = None
    limit: int = 50
    cursor: str | None = None
    connection_revoked: bool = False
    scopes: frozenset[str] = frozenset({"memory:read"})


@dataclass(frozen=True, slots=True)
class InboxResult:
    candidates: tuple[Memory, ...]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ConfirmCandidateCommand:
    tenant_id: str
    owner_id: str
    connection_id: str
    memory_id: UUID
    expected_version: int
    idempotency_key: str
    content: str | None = None
    memory_type: MemoryType | None = None
    space: str | None = None
    actor_reason: str = "user_confirmed_inbox"
    connection_revoked: bool = False
    scopes: frozenset[str] = frozenset({"memory:write"})


@dataclass(frozen=True, slots=True)
class PinMemoryCommand:
    tenant_id: str
    owner_id: str
    connection_id: str
    memory_id: UUID
    expected_version: int
    pinned: bool
    idempotency_key: str
    connection_revoked: bool = False
    scopes: frozenset[str] = frozenset({"memory:write"})


@dataclass(frozen=True, slots=True)
class DiscardCandidateCommand:
    tenant_id: str
    owner_id: str
    connection_id: str
    memory_id: UUID
    expected_version: int
    idempotency_key: str
    reason_code: str = "user_requested_memory"
    connection_revoked: bool = False
    scopes: frozenset[str] = frozenset({"memory:delete"})


@dataclass(frozen=True, slots=True)
class DiscardResult:
    memory_id: UUID
    forgotten: bool


@dataclass(frozen=True, slots=True)
class RecallMemoryCommand:
    tenant_id: str
    owner_id: str
    connection_id: str
    query: str
    context_space: str | None
    include_spaces: tuple[str, ...] = ()
    memory_types: frozenset[MemoryType] | None = None
    states: frozenset[MemoryState] = frozenset({MemoryState.CONFIRMED, MemoryState.PINNED})
    allow_mental_notes: bool = False
    limit: int = 5
    candidate_limit: int = 50
    threshold: float = 0.78
    space_policy: SpacePolicy = field(default_factory=SpacePolicy)
    connection_revoked: bool = False
    scopes: frozenset[str] = frozenset({"memory:read"})


@dataclass(frozen=True, slots=True)
class RecallResult:
    items: tuple[SearchMemoryItem, ...]
    count: int
    profile_id: str
    profile_version: str


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
