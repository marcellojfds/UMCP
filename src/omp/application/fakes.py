"""Deterministic in-memory adapters for unit and MCP contract tests."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from uuid import UUID

from omp.domain import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    ImportConflictError,
    Memory,
    MemoryState,
    MemoryVersion,
    NotFoundError,
    Relation,
    RelationConflictError,
    RestoreBlockedByTombstoneError,
    VersionConflictError,
)

from .models import ImportResult, MemoryExportRecord, MemoryImportRecord, SearchFilters
from .ports import (
    CreateMemoryResult,
    EmbeddingProfile,
    IdempotencyClaim,
    IdempotencyLookup,
    IdempotencyOperationType,
    MemorySearchCandidate,
)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return -1.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


@dataclass
class InMemoryStore:
    memories: dict[UUID, Memory] = field(default_factory=dict)
    vectors: dict[UUID, tuple[float, ...]] = field(default_factory=dict)
    fingerprints: dict[tuple[str, str], str] = field(default_factory=dict)
    history_by_memory: dict[UUID, list[MemoryVersion]] = field(default_factory=dict)
    relations: dict[tuple[str, UUID, UUID, str], Relation] = field(default_factory=dict)
    idempotency_operations: dict[tuple[str, str, str], StoredIdempotencyOperation] = field(
        default_factory=dict
    )
    tombstones: set[tuple[str, str | None, UUID]] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    transaction_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@dataclass
class StoredIdempotencyOperation:
    fingerprint: str
    status: str = "in_progress"
    memory_id: UUID | None = None
    result_version: int | None = None
    result_status: str | None = None


class InMemoryIdempotencyRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def claim(
        self,
        *,
        owner_id: str,
        operation_type: IdempotencyOperationType,
        idempotency_key: str,
        fingerprint: str,
    ) -> IdempotencyClaim:
        key = (owner_id, operation_type.value, idempotency_key)
        async with self._store.lock:
            prior = self._store.idempotency_operations.get(key)
            if prior is None:
                self._store.idempotency_operations[key] = StoredIdempotencyOperation(
                    fingerprint=fingerprint
                )
                return IdempotencyClaim(
                    owner_id=owner_id,
                    operation_type=operation_type,
                    idempotency_key=idempotency_key,
                    fingerprint=fingerprint,
                    replay=False,
                )
            if prior.fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    "idempotency_key was already used for another operation"
                )
            if prior.status != "completed":
                raise IdempotencyInProgressError("idempotency operation is still in progress")
            return IdempotencyClaim(
                owner_id=owner_id,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                replay=True,
                memory_id=prior.memory_id,
                result_version=prior.result_version,
                result_status=prior.result_status,
            )

    async def complete(
        self,
        *,
        claim: IdempotencyClaim,
        memory_id: UUID | None,
        result_version: int | None,
        result_status: str,
    ) -> None:
        key = (claim.owner_id, claim.operation_type.value, claim.idempotency_key)
        async with self._store.lock:
            operation = self._store.idempotency_operations.get(key)
            if operation is None or operation.fingerprint != claim.fingerprint:
                raise IdempotencyConflictError("idempotency operation claim is missing")
            if operation.status == "completed":
                return
            operation.status = "completed"
            operation.memory_id = memory_id
            operation.result_version = result_version
            operation.result_status = result_status


class InMemoryMemoryRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get(
        self, *, owner_id: str, memory_id: UUID, tenant_id: str | None = None
    ) -> Memory | None:
        memory = self._store.memories.get(memory_id)
        if memory is None or memory.owner_id != owner_id:
            return None
        if tenant_id is not None and memory.tenant_id != tenant_id:
            return None
        return deepcopy(memory)

    async def get_version(
        self, *, owner_id: str, memory_id: UUID, version: int, tenant_id: str | None = None
    ) -> Memory | None:
        current = await self.get(owner_id=owner_id, memory_id=memory_id, tenant_id=tenant_id)
        if current is None:
            return None
        if current.version == version:
            return current
        for snapshot in self._store.history_by_memory.get(memory_id, []):
            if snapshot.version == version:
                return replace(
                    current,
                    content=snapshot.content,
                    memory_type=snapshot.memory_type,
                    importance=snapshot.importance,
                    confidence=snapshot.confidence,
                    state=snapshot.state,
                    version=snapshot.version,
                    updated_at=snapshot.changed_at,
                    occurred_at=snapshot.occurred_at,
                    space=snapshot.space,
                    provenance=snapshot.provenance,
                )
        return None

    async def find_by_idempotency_key(
        self, *, owner_id: str, idempotency_key: str
    ) -> IdempotencyLookup | None:
        for (stored_owner, stored_key), fingerprint in self._store.fingerprints.items():
            if stored_owner == owner_id and stored_key == idempotency_key:
                memory = next(
                    value
                    for value in self._store.memories.values()
                    if value.owner_id == owner_id and value.idempotency_key == idempotency_key
                )
                return IdempotencyLookup(memory=deepcopy(memory), fingerprint=fingerprint)
        return None

    async def create(
        self,
        *,
        memory: Memory,
        fingerprint: str,
        embedding: Sequence[float],
    ) -> CreateMemoryResult:
        async with self._store.lock:
            if memory.idempotency_key:
                key = (memory.owner_id, memory.idempotency_key)
                prior_fingerprint = self._store.fingerprints.get(key)
                if prior_fingerprint is not None:
                    if prior_fingerprint != fingerprint:
                        raise IdempotencyConflictError(
                            "idempotency_key was already used for another memory"
                        )
                    prior = next(
                        value
                        for value in self._store.memories.values()
                        if value.owner_id == memory.owner_id
                        and value.idempotency_key == memory.idempotency_key
                    )
                    return CreateMemoryResult(memory=deepcopy(prior), created=False)
                self._store.fingerprints[key] = fingerprint
            self._store.memories[memory.id] = deepcopy(memory)
            self._store.vectors[memory.id] = tuple(float(item) for item in embedding)
            self._store.history_by_memory[memory.id] = [memory.snapshot(change_reason="created")]
            return CreateMemoryResult(memory=deepcopy(memory), created=True)

    async def update(
        self,
        *,
        memory: Memory,
        expected_version: int,
        version_snapshot: MemoryVersion,
        embedding: Sequence[float],
    ) -> Memory:
        async with self._store.lock:
            current = self._store.memories.get(memory.id)
            if current is None or current.owner_id != memory.owner_id:
                raise NotFoundError("memory was not found")
            if current.version != expected_version:
                raise VersionConflictError("memory version has changed")
            self._store.history_by_memory[memory.id].append(deepcopy(version_snapshot))
            self._store.memories[memory.id] = deepcopy(memory)
            self._store.vectors[memory.id] = tuple(float(item) for item in embedding)
            return deepcopy(memory)

    async def search_candidates(
        self,
        *,
        owner_id: str,
        query_embedding: Sequence[float],
        profile: EmbeddingProfile,
        filters: SearchFilters,
        limit: int,
        tenant_id: str | None = None,
    ) -> Sequence[MemorySearchCandidate]:
        candidates: list[MemorySearchCandidate] = []
        for memory_id, memory in self._store.memories.items():
            if memory.owner_id != owner_id:
                continue
            if tenant_id is not None and memory.tenant_id != tenant_id:
                continue
            if memory.state not in filters.states:
                continue
            if filters.memory_types and memory.memory_type not in filters.memory_types:
                continue
            if filters.space is not None and memory.space != filters.space:
                continue
            if filters.min_importance is not None and memory.importance < filters.min_importance:
                continue
            if filters.min_confidence is not None and memory.confidence < filters.min_confidence:
                continue
            if memory.embedding is None or memory.embedding != profile.descriptor():
                continue
            candidates.append(
                MemorySearchCandidate(
                    memory=deepcopy(memory),
                    similarity=(
                        cosine_similarity(query_embedding, self._store.vectors[memory_id]) + 1
                    )
                    / 2,
                    profile=profile,
                )
            )
        candidates.sort(key=lambda candidate: (-candidate.similarity, str(candidate.memory.id)))
        return candidates[:limit]

    async def forget(self, *, owner_id: str, memory_id: UUID, tenant_id: str | None = None) -> bool:
        async with self._store.lock:
            memory = self._store.memories.get(memory_id)
            if memory is None or memory.owner_id != owner_id:
                return False
            if tenant_id is not None and memory.tenant_id != tenant_id:
                return False
            del self._store.memories[memory_id]
            self._store.vectors.pop(memory_id, None)
            self._store.history_by_memory.pop(memory_id, None)
            if memory.idempotency_key:
                self._store.fingerprints.pop((owner_id, memory.idempotency_key), None)
            self._store.relations = {
                key: relation
                for key, relation in self._store.relations.items()
                if relation.source_id != memory_id and relation.target_id != memory_id
            }
            self._store.tombstones.add((owner_id, memory.tenant_id, memory_id))
            return True

    async def list_candidates(
        self, *, owner_id: str, tenant_id: str | None, space: str | None, limit: int
    ) -> Sequence[Memory]:
        values = [
            deepcopy(memory)
            for memory in self._store.memories.values()
            if memory.owner_id == owner_id
            and (tenant_id is None or memory.tenant_id == tenant_id)
            and memory.state == MemoryState.CANDIDATE
            and (space is None or memory.space == space)
        ]
        values.sort(key=lambda item: (item.created_at, str(item.id)))
        return tuple(values[:limit])

    async def add_relation(self, *, relation: Relation) -> Relation:
        source = await self.get(owner_id=relation.owner_id, memory_id=relation.source_id)
        target = await self.get(owner_id=relation.owner_id, memory_id=relation.target_id)
        if source is None or target is None:
            raise NotFoundError("both related memories must exist for this owner")
        key = (
            relation.owner_id,
            relation.source_id,
            relation.target_id,
            relation.relation_type.value,
        )
        async with self._store.lock:
            if key in self._store.relations:
                raise RelationConflictError("relation already exists")
            self._store.relations[key] = relation
        return relation

    async def list_relations(self, *, owner_id: str, memory_id: UUID) -> Sequence[Relation]:
        return tuple(
            relation
            for relation in self._store.relations.values()
            if relation.owner_id == owner_id
            and (relation.source_id == memory_id or relation.target_id == memory_id)
        )

    async def history(self, *, owner_id: str, memory_id: UUID) -> Sequence[MemoryVersion]:
        memory = await self.get(owner_id=owner_id, memory_id=memory_id)
        if memory is None:
            raise NotFoundError("memory was not found")
        return tuple(deepcopy(self._store.history_by_memory.get(memory_id, [])))


class InMemoryMemoryAdminRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self._memories = InMemoryMemoryRepository(store)

    async def export_memories(
        self, *, owner_id: str, include_embeddings: bool
    ) -> Sequence[MemoryExportRecord]:
        records: list[MemoryExportRecord] = []
        for memory in sorted(self._store.memories.values(), key=lambda item: str(item.id)):
            if memory.owner_id != owner_id:
                continue
            record = await self.export_memory(
                owner_id=owner_id, memory_id=memory.id, include_embeddings=include_embeddings
            )
            if record is not None:
                records.append(record)
        return tuple(records)

    async def export_memory(
        self, *, owner_id: str, memory_id: UUID, include_embeddings: bool
    ) -> MemoryExportRecord | None:
        memory = await self._memories.get(owner_id=owner_id, memory_id=memory_id)
        if memory is None:
            return None
        relations = await self._memories.list_relations(owner_id=owner_id, memory_id=memory_id)
        fingerprint = (
            self._store.fingerprints.get((owner_id, memory.idempotency_key))
            if memory.idempotency_key is not None
            else None
        )
        vector = self._store.vectors.get(memory_id) if include_embeddings else None
        return MemoryExportRecord(
            memory=memory,
            history=tuple(await self._memories.history(owner_id=owner_id, memory_id=memory_id)),
            relations=tuple(relations),
            embedding=vector,
            write_fingerprint=fingerprint,
        )

    async def import_memories(self, *, records: Sequence[MemoryImportRecord]) -> ImportResult:
        imported = 0
        replayed = 0
        async with self._store.lock:
            for record in records:
                current = self._store.memories.get(record.memory.id)
                if (
                    record.memory.owner_id,
                    record.memory.tenant_id,
                    record.memory.id,
                ) in self._store.tombstones:
                    raise RestoreBlockedByTombstoneError("memory restore is blocked by a tombstone")
                if current is not None:
                    if current != record.memory:
                        raise ImportConflictError("import conflicts with existing memory")
                    replayed += 1
                    continue
                if record.embedding is None:
                    raise ValueError("prepared import record must contain an embedding")
                self._store.memories[record.memory.id] = deepcopy(record.memory)
                self._store.vectors[record.memory.id] = tuple(record.embedding)
                self._store.history_by_memory[record.memory.id] = deepcopy(list(record.history))
                if record.memory.idempotency_key is not None:
                    self._store.fingerprints[
                        (record.memory.owner_id, record.memory.idempotency_key)
                    ] = record.write_fingerprint or ""
                imported += 1

            for record in records:
                for relation in record.relations:
                    key = (
                        relation.owner_id,
                        relation.source_id,
                        relation.target_id,
                        relation.relation_type.value,
                    )
                    if key not in self._store.relations:
                        self._store.relations[key] = deepcopy(relation)
        return ImportResult(imported=imported, replayed=replayed)

    async def is_tombstoned(
        self, *, owner_id: str, memory_id: UUID, tenant_id: str | None = None
    ) -> bool:
        return (owner_id, tenant_id, memory_id) in self._store.tombstones


class InMemoryUnitOfWork:
    def __init__(self, store: InMemoryStore | None = None) -> None:
        self.store = store or InMemoryStore()
        self.memories = InMemoryMemoryRepository(self.store)
        self.idempotency = InMemoryIdempotencyRepository(self.store)
        self.admin = InMemoryMemoryAdminRepository(self.store)
        self._snapshot: (
            tuple[
                dict[UUID, Memory],
                dict[UUID, tuple[float, ...]],
                dict[tuple[str, str], str],
                dict[UUID, list[MemoryVersion]],
                dict[tuple[str, UUID, UUID, str], Relation],
                dict[tuple[str, str, str], StoredIdempotencyOperation],
                set[tuple[str, str | None, UUID]],
            ]
            | None
        ) = None

    async def __aenter__(self) -> InMemoryUnitOfWork:
        await self.store.transaction_lock.acquire()
        self._snapshot = (
            deepcopy(self.store.memories),
            deepcopy(self.store.vectors),
            deepcopy(self.store.fingerprints),
            deepcopy(self.store.history_by_memory),
            deepcopy(self.store.relations),
            deepcopy(self.store.idempotency_operations),
            deepcopy(self.store.tombstones),
        )
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if exc_type is not None and self._snapshot is not None:
                (
                    self.store.memories,
                    self.store.vectors,
                    self.store.fingerprints,
                    self.store.history_by_memory,
                    self.store.relations,
                    self.store.idempotency_operations,
                    self.store.tombstones,
                ) = self._snapshot
        finally:
            self.store.transaction_lock.release()


class InMemoryUnitOfWorkFactory:
    def __init__(self, store: InMemoryStore | None = None) -> None:
        self.store = store or InMemoryStore()

    def __call__(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self.store)
