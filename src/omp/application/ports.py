"""Stable internal ports consumed by application services and adapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from omp.domain import EmbeddingDescriptor, Memory, MemoryVersion, Relation

from .models import ImportResult, MemoryExportRecord, MemoryImportRecord, SearchFilters


@dataclass(frozen=True, slots=True)
class EmbeddingProfile:
    id: str
    version: str
    dimension: int
    metric: str = "cosine"

    def descriptor(self) -> EmbeddingDescriptor:
        return EmbeddingDescriptor(self.id, self.version, self.dimension, self.metric)


@dataclass(frozen=True, slots=True)
class IdempotencyLookup:
    memory: Memory
    fingerprint: str


class IdempotencyOperationType(StrEnum):
    UPDATE = "update"
    FORGET = "forget"
    CONFIRM = "confirm"
    PIN = "pin"
    DISCARD = "discard"


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    owner_id: str
    operation_type: IdempotencyOperationType
    idempotency_key: str
    fingerprint: str
    replay: bool
    memory_id: UUID | None = None
    result_version: int | None = None
    result_status: str | None = None


@dataclass(frozen=True, slots=True)
class CreateMemoryResult:
    memory: Memory
    created: bool


@dataclass(frozen=True, slots=True)
class MemorySearchCandidate:
    memory: Memory
    similarity: float
    profile: EmbeddingProfile


class EmbeddingProvider(Protocol):
    @property
    def profile(self) -> EmbeddingProfile: ...

    async def embed(self, text: str, *, query: bool = False) -> Sequence[float]: ...


class MemoryRepository(Protocol):
    async def get(
        self, *, owner_id: str, memory_id: UUID, tenant_id: str | None = None
    ) -> Memory | None: ...

    async def get_version(
        self, *, owner_id: str, memory_id: UUID, version: int, tenant_id: str | None = None
    ) -> Memory | None: ...

    async def find_by_idempotency_key(
        self, *, owner_id: str, idempotency_key: str
    ) -> IdempotencyLookup | None: ...

    async def create(
        self,
        *,
        memory: Memory,
        fingerprint: str,
        embedding: Sequence[float],
    ) -> CreateMemoryResult: ...

    async def update(
        self,
        *,
        memory: Memory,
        expected_version: int,
        version_snapshot: MemoryVersion,
        embedding: Sequence[float],
    ) -> Memory: ...

    async def search_candidates(
        self,
        *,
        owner_id: str,
        tenant_id: str | None = None,
        query_embedding: Sequence[float],
        profile: EmbeddingProfile,
        filters: SearchFilters,
        limit: int,
    ) -> Sequence[MemorySearchCandidate]: ...

    async def forget(
        self, *, owner_id: str, memory_id: UUID, tenant_id: str | None = None
    ) -> bool: ...

    async def list_candidates(
        self, *, owner_id: str, tenant_id: str | None, space: str | None, limit: int
    ) -> Sequence[Memory]: ...

    async def add_relation(self, *, relation: Relation) -> Relation: ...

    async def list_relations(self, *, owner_id: str, memory_id: UUID) -> Sequence[Relation]: ...

    async def history(self, *, owner_id: str, memory_id: UUID) -> Sequence[MemoryVersion]: ...

    async def list_for_reembedding(
        self, *, owner_id: str, after_memory_id: UUID | None, limit: int
    ) -> Sequence[Memory]: ...

    async def upsert_embedding_profile(
        self,
        *,
        memory_id: UUID,
        expected_version: int,
        profile: EmbeddingProfile,
        embedding: Sequence[float],
    ) -> bool: ...

    async def semantic_coverage(
        self, *, owner_id: str, profile: EmbeddingProfile
    ) -> tuple[int, int]: ...

    async def cutover_embedding_profile(
        self, *, owner_id: str, profile: EmbeddingProfile
    ) -> int: ...


class IdempotencyRepository(Protocol):
    async def claim(
        self,
        *,
        owner_id: str,
        operation_type: IdempotencyOperationType,
        idempotency_key: str,
        fingerprint: str,
    ) -> IdempotencyClaim: ...

    async def complete(
        self,
        *,
        claim: IdempotencyClaim,
        memory_id: UUID | None,
        result_version: int | None,
        result_status: str,
    ) -> None: ...


class MemoryAdminRepository(Protocol):
    async def export_memories(
        self, *, owner_id: str, include_embeddings: bool
    ) -> Sequence[MemoryExportRecord]: ...

    async def export_memory(
        self, *, owner_id: str, memory_id: UUID, include_embeddings: bool
    ) -> MemoryExportRecord | None: ...

    async def import_memories(self, *, records: Sequence[MemoryImportRecord]) -> ImportResult: ...

    async def is_tombstoned(
        self, *, owner_id: str, memory_id: UUID, tenant_id: str | None = None
    ) -> bool: ...


class UnitOfWork(Protocol):
    memories: MemoryRepository
    idempotency: IdempotencyRepository
    admin: MemoryAdminRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
