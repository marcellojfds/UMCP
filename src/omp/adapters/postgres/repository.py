"""Async PostgreSQL repository with mandatory owner isolation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, delete, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from omp.application.models import (
    ImportResult,
    MemoryExportRecord,
    MemoryImportRecord,
    SearchFilters,
)
from omp.application.ports import (
    CreateMemoryResult,
    EmbeddingProfile,
    IdempotencyClaim,
    IdempotencyLookup,
    IdempotencyOperationType,
    MemorySearchCandidate,
)
from omp.cloud.tenant import current_tenant, current_tenant_or_none, set_tenant_context
from omp.config import OMPSettings
from omp.domain import (
    EmbeddingDescriptor,
    IdempotencyConflictError,
    IdempotencyInProgressError,
    ImportConflictError,
    Memory,
    MemoryState,
    MemoryType,
    MemoryVersion,
    NotFoundError,
    Provenance,
    Relation,
    RelationConflictError,
    RelationType,
    SourceType,
    VersionConflictError,
)

from .schema import (
    idempotency_operations,
    memories,
    memory_embeddings,
    memory_embeddings_semantic,
    memory_relations,
    memory_versions,
)


def _provenance_to_json(provenance: Provenance) -> dict[str, object]:
    return {
        "source_type": provenance.source_type.value,
        "source_id": provenance.source_id,
        "source_model": provenance.source_model,
        "captured_at": provenance.captured_at.isoformat(),
        "evidence": list(provenance.evidence),
    }


def _provenance_from_json(payload: dict[str, object]) -> Provenance:
    evidence = payload.get("evidence", [])
    return Provenance(
        source_type=SourceType(str(payload["source_type"])),
        source_id=str(payload["source_id"]) if payload.get("source_id") else None,
        source_model=str(payload["source_model"]) if payload.get("source_model") else None,
        captured_at=datetime.fromisoformat(str(payload["captured_at"])),
        evidence=tuple(str(item) for item in evidence) if isinstance(evidence, list) else (),
    )


def _memory_from_row(row: Any) -> Memory:
    mapping = row._mapping
    return Memory(
        id=mapping["id"],
        owner_id=mapping["owner_id"],
        content=mapping["content"],
        memory_type=MemoryType(mapping["memory_type"]),
        importance=mapping["importance"],
        confidence=mapping["confidence"],
        state=MemoryState(mapping["state"]),
        version=mapping["version"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
        occurred_at=mapping["occurred_at"],
        space=mapping["space"],
        provenance=_provenance_from_json(mapping["provenance"]),
        embedding=EmbeddingDescriptor(
            profile_id=mapping["embedding_profile_id"],
            profile_version=mapping["embedding_profile_version"],
            dimension=mapping["embedding_dimension"],
            metric=mapping["embedding_metric"],
        ),
        idempotency_key=mapping["idempotency_key"],
    )


class PostgresIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(
        self,
        *,
        owner_id: str,
        operation_type: IdempotencyOperationType,
        idempotency_key: str,
        fingerprint: str,
    ) -> IdempotencyClaim:
        where = (
            idempotency_operations.c.owner_id == owner_id,
            idempotency_operations.c.operation_type == operation_type.value,
            idempotency_operations.c.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(
            select(idempotency_operations).where(*where).with_for_update()
        )
        row = result.first()
        if row is None:
            inserted = await self._session.execute(
                pg_insert(idempotency_operations)
                .values(
                    {
                        "owner_id": owner_id,
                        "tenant_id": current_tenant_or_none(),
                        "operation_type": operation_type.value,
                        "idempotency_key": idempotency_key,
                        "fingerprint": fingerprint,
                        "status": "in_progress",
                        "claimed_at": datetime.now(UTC),
                    }
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        idempotency_operations.c.owner_id,
                        idempotency_operations.c.operation_type,
                        idempotency_operations.c.idempotency_key,
                    ]
                )
                .returning(idempotency_operations)
            )
            inserted_row = inserted.first()
            if inserted_row is not None:
                return IdempotencyClaim(
                    owner_id=owner_id,
                    operation_type=operation_type,
                    idempotency_key=idempotency_key,
                    fingerprint=fingerprint,
                    replay=False,
                )
            result = await self._session.execute(
                select(idempotency_operations).where(*where).with_for_update()
            )
            row = result.first()
        if row is None:
            raise IdempotencyConflictError("idempotency operation claim could not be established")
        mapping = row._mapping
        if mapping["fingerprint"] != fingerprint:
            raise IdempotencyConflictError("idempotency_key was already used for another operation")
        if mapping["status"] != "completed":
            raise IdempotencyInProgressError("idempotency operation is still in progress")
        return IdempotencyClaim(
            owner_id=owner_id,
            operation_type=operation_type,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            replay=True,
            memory_id=mapping["memory_id"],
            result_version=mapping["result_version"],
            result_status=mapping["result_status"],
        )

    async def complete(
        self,
        *,
        claim: IdempotencyClaim,
        memory_id: UUID | None,
        result_version: int | None,
        result_status: str,
    ) -> None:
        statement = (
            update(idempotency_operations)
            .where(
                idempotency_operations.c.owner_id == claim.owner_id,
                idempotency_operations.c.operation_type == claim.operation_type.value,
                idempotency_operations.c.idempotency_key == claim.idempotency_key,
                idempotency_operations.c.fingerprint == claim.fingerprint,
                idempotency_operations.c.status == "in_progress",
            )
            .values(
                status="completed",
                memory_id=memory_id,
                result_version=result_version,
                result_status=result_status,
                completed_at=datetime.now(UTC),
            )
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            raise IdempotencyConflictError("idempotency operation was not claimable")


class PostgresMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, owner_id: str, memory_id: UUID) -> Memory | None:
        stmt = select(memories).where(memories.c.owner_id == owner_id, memories.c.id == memory_id)
        result = await self._session.execute(stmt)
        row = result.first()
        return _memory_from_row(row) if row is not None else None

    async def get_version(self, *, owner_id: str, memory_id: UUID, version: int) -> Memory | None:
        current = await self.get(owner_id=owner_id, memory_id=memory_id)
        if current is None:
            return None
        if current.version == version:
            return current
        statement = (
            select(memory_versions)
            .join(memories, memories.c.id == memory_versions.c.memory_id)
            .where(
                memories.c.owner_id == owner_id,
                memories.c.id == memory_id,
                memory_versions.c.version == version,
            )
        )
        result = await self._session.execute(statement)
        row = result.first()
        if row is None:
            return None
        snapshot = self._version_from_row(row)
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

    async def find_by_idempotency_key(
        self, *, owner_id: str, idempotency_key: str
    ) -> IdempotencyLookup | None:
        stmt = select(memories).where(
            memories.c.owner_id == owner_id,
            memories.c.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        memory = _memory_from_row(row)
        fingerprint = row._mapping["idempotency_fingerprint"]
        return IdempotencyLookup(memory=memory, fingerprint=fingerprint)

    async def create(
        self,
        *,
        memory: Memory,
        fingerprint: str,
        embedding: Sequence[float],
    ) -> CreateMemoryResult:
        values = self._memory_values(memory, fingerprint=fingerprint)
        statement: Any = pg_insert(memories).values(values)
        if memory.idempotency_key:
            statement = statement.on_conflict_do_nothing(
                index_elements=[memories.c.owner_id, memories.c.idempotency_key]
            )
        statement = statement.returning(memories)
        try:
            result = await self._session.execute(statement)
        except IntegrityError as exc:
            raise IdempotencyConflictError(
                "memory idempotency constraint rejected the write"
            ) from exc
        row = result.first()
        if row is None:
            prior = await self.find_by_idempotency_key(
                owner_id=memory.owner_id, idempotency_key=memory.idempotency_key or ""
            )
            if prior is None or prior.fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    "idempotency_key was already used for another memory"
                )
            return CreateMemoryResult(memory=prior.memory, created=False)
        embedding_table = self._embedding_table(
            memory.embedding.dimension if memory.embedding else 0
        )
        await self._session.execute(
            insert(embedding_table).values(self._embedding_values(memory, embedding))
        )
        await self._session.execute(
            insert(memory_versions).values(
                self._version_values(memory.snapshot(change_reason="created"))
            )
        )
        return CreateMemoryResult(memory=memory, created=True)

    async def update(
        self,
        *,
        memory: Memory,
        expected_version: int,
        version_snapshot: MemoryVersion,
        embedding: Sequence[float],
    ) -> Memory:
        values = self._memory_values(memory, fingerprint=None)
        for immutable_field in (
            "id",
            "owner_id",
            "created_at",
            "idempotency_key",
            "idempotency_fingerprint",
        ):
            values.pop(immutable_field, None)
        statement = (
            update(memories)
            .where(
                memories.c.id == memory.id,
                memories.c.owner_id == memory.owner_id,
                memories.c.version == expected_version,
            )
            .values(values)
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            current = await self.get(owner_id=memory.owner_id, memory_id=memory.id)
            if current is None:
                raise NotFoundError("memory was not found")
            raise VersionConflictError("memory version has changed")
        await self._session.execute(
            insert(memory_versions).values(self._version_values(version_snapshot))
        )
        embedding_table = self._embedding_table(
            memory.embedding.dimension if memory.embedding else 0
        )
        await self._session.execute(
            update(embedding_table)
            .where(embedding_table.c.memory_id == memory.id)
            .values(self._embedding_values(memory, embedding, include_memory_id=False))
        )
        return memory

    async def search_candidates(
        self,
        *,
        owner_id: str,
        query_embedding: Sequence[float],
        profile: EmbeddingProfile,
        filters: SearchFilters,
        limit: int,
    ) -> Sequence[MemorySearchCandidate]:
        embedding_table = self._embedding_table(profile.dimension)
        query_vector = bindparam(
            "query_embedding",
            type_=embedding_table.c.vector.type,
        )
        similarity = (1 - embedding_table.c.vector.cosine_distance(query_vector)).label(
            "similarity"
        )
        conditions = [
            memories.c.owner_id == owner_id,
            embedding_table.c.profile_id == profile.id,
            embedding_table.c.profile_version == profile.version,
            (
                embedding_table.c.source_version == memories.c.version
                if profile.dimension == 384
                else True
            ),
            embedding_table.c.dimension == profile.dimension,
            memories.c.state.in_([state.value for state in filters.states]),
        ]
        if filters.memory_types:
            conditions.append(
                memories.c.memory_type.in_([item.value for item in filters.memory_types])
            )
        if filters.space is not None:
            conditions.append(memories.c.space == filters.space)
        if filters.min_importance is not None:
            conditions.append(memories.c.importance >= filters.min_importance)
        if filters.min_confidence is not None:
            conditions.append(memories.c.confidence >= filters.min_confidence)
        statement = (
            select(memories, similarity)
            .join(embedding_table, embedding_table.c.memory_id == memories.c.id)
            .where(*conditions)
            .order_by(similarity.desc(), memories.c.id.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement, {"query_embedding": list(query_embedding)})
        candidates = []
        for row in result:
            candidates.append(
                MemorySearchCandidate(
                    memory=_memory_from_row(row),
                    similarity=float(row._mapping["similarity"]),
                    profile=profile,
                )
            )
        return candidates

    async def forget(self, *, owner_id: str, memory_id: UUID) -> bool:
        statement = delete(memories).where(
            memories.c.owner_id == owner_id, memories.c.id == memory_id
        )
        result = await self._session.execute(statement)
        return bool(result.rowcount)

    async def add_relation(self, *, relation: Relation) -> Relation:
        source = await self.get(owner_id=relation.owner_id, memory_id=relation.source_id)
        target = await self.get(owner_id=relation.owner_id, memory_id=relation.target_id)
        if source is None or target is None:
            raise NotFoundError("both related memories must exist for this owner")
        statement = pg_insert(memory_relations).values(
            {
                "owner_id": relation.owner_id,
                "tenant_id": current_tenant_or_none(),
                "source_id": relation.source_id,
                "target_id": relation.target_id,
                "relation_type": relation.relation_type.value,
                "created_at": relation.created_at,
            }
        )
        try:
            await self._session.execute(statement)
        except IntegrityError as exc:
            raise RelationConflictError(
                "relation already exists or violates ownership constraints"
            ) from exc
        return relation

    async def list_relations(self, *, owner_id: str, memory_id: UUID) -> Sequence[Relation]:
        statement = select(memory_relations).where(
            memory_relations.c.owner_id == owner_id,
            (memory_relations.c.source_id == memory_id)
            | (memory_relations.c.target_id == memory_id),
        )
        result = await self._session.execute(statement)
        return tuple(self._relation_from_row(row) for row in result)

    async def history(self, *, owner_id: str, memory_id: UUID) -> Sequence[MemoryVersion]:
        if await self.get(owner_id=owner_id, memory_id=memory_id) is None:
            raise NotFoundError("memory was not found")
        statement = (
            select(memory_versions)
            .join(memories, memories.c.id == memory_versions.c.memory_id)
            .where(memories.c.owner_id == owner_id, memory_versions.c.memory_id == memory_id)
            .order_by(memory_versions.c.version.asc())
        )
        result = await self._session.execute(statement)
        return tuple(self._version_from_row(row) for row in result)

    async def list_for_reembedding(
        self, *, owner_id: str, after_memory_id: UUID | None, limit: int
    ) -> Sequence[Memory]:
        conditions = [memories.c.owner_id == owner_id, memories.c.embedding_dimension == 64]
        if after_memory_id is not None:
            conditions.append(memories.c.id > after_memory_id)
        statement = select(memories).where(*conditions).order_by(memories.c.id.asc()).limit(limit)
        result = await self._session.execute(statement)
        return tuple(_memory_from_row(row) for row in result)

    async def upsert_embedding_profile(
        self,
        *,
        memory_id: UUID,
        expected_version: int,
        profile: EmbeddingProfile,
        embedding: Sequence[float],
    ) -> bool:
        if profile.dimension != 384:
            raise ValueError("re-embedding requires the semantic 384d profile")
        current_version = await self._session.scalar(
            select(memories.c.version).where(
                memories.c.id == memory_id, memories.c.version == expected_version
            )
        )
        if current_version is None:
            return False
        table = self._embedding_table(profile.dimension)
        statement = pg_insert(table).values(
            {
                "memory_id": memory_id,
                "tenant_id": current_tenant_or_none(),
                "profile_id": profile.id,
                "profile_version": profile.version,
                "source_version": expected_version,
                "dimension": profile.dimension,
                "metric": profile.metric,
                "vector": list(embedding),
            }
        )
        statement = statement.on_conflict_do_update(
            index_elements=[table.c.memory_id, table.c.profile_id, table.c.profile_version],
            set_={
                "source_version": expected_version,
                "dimension": profile.dimension,
                "metric": profile.metric,
                "vector": list(embedding),
            },
        )
        await self._session.execute(statement)
        return True

    async def semantic_coverage(
        self, *, owner_id: str, profile: EmbeddingProfile
    ) -> tuple[int, int]:
        eligible = await self._session.scalar(
            select(func.count())
            .select_from(memories)
            .where(memories.c.owner_id == owner_id, memories.c.embedding_dimension == 64)
        )
        covered = await self._session.scalar(
            select(func.count())
            .select_from(memories.join(memory_embeddings_semantic))
            .where(
                memories.c.owner_id == owner_id,
                memories.c.embedding_dimension == 64,
                memory_embeddings_semantic.c.profile_id == profile.id,
                memory_embeddings_semantic.c.profile_version == profile.version,
                memory_embeddings_semantic.c.source_version == memories.c.version,
            )
        )
        return int(eligible or 0), int(covered or 0)

    async def cutover_embedding_profile(self, *, owner_id: str, profile: EmbeddingProfile) -> int:
        eligible, covered = await self.semantic_coverage(owner_id=owner_id, profile=profile)
        if eligible != covered:
            raise RuntimeError("semantic embedding coverage is incomplete")
        result = await self._session.execute(
            update(memories)
            .where(memories.c.owner_id == owner_id, memories.c.embedding_dimension == 64)
            .values(
                embedding_profile_id=profile.id,
                embedding_profile_version=profile.version,
                embedding_dimension=profile.dimension,
                embedding_metric=profile.metric,
            )
        )
        return int(result.rowcount or 0)

    @staticmethod
    def _memory_values(memory: Memory, *, fingerprint: str | None) -> dict[str, object]:
        if memory.embedding is None:
            raise ValueError("memory must have an embedding descriptor for storage")
        return {
            "id": memory.id,
            "owner_id": memory.owner_id,
            "tenant_id": current_tenant_or_none(),
            "space": memory.space,
            "memory_type": memory.memory_type.value,
            "content": memory.content,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "state": memory.state.value,
            "version": memory.version,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "occurred_at": memory.occurred_at,
            "provenance": _provenance_to_json(memory.provenance),
            "embedding_profile_id": memory.embedding.profile_id,
            "embedding_profile_version": memory.embedding.profile_version,
            "embedding_dimension": memory.embedding.dimension,
            "embedding_metric": memory.embedding.metric,
            "idempotency_key": memory.idempotency_key,
            "idempotency_fingerprint": fingerprint,
        }

    @staticmethod
    def _embedding_values(
        memory: Memory, embedding: Sequence[float], *, include_memory_id: bool = True
    ) -> dict[str, object]:
        if memory.embedding is None:
            raise ValueError("memory must have an embedding descriptor for storage")
        values: dict[str, object] = {
            "tenant_id": current_tenant_or_none(),
            "profile_id": memory.embedding.profile_id,
            "profile_version": memory.embedding.profile_version,
            "dimension": memory.embedding.dimension,
            "metric": memory.embedding.metric,
            "vector": list(embedding),
        }
        # The parallel semantic table ties a vector to the exact aggregate
        # version it represents. Hash/v1 stays in its original 64d table and
        # intentionally receives no additional column or value.
        if memory.embedding.dimension == 384:
            values["source_version"] = memory.version
        if include_memory_id:
            values["memory_id"] = memory.id
        return values

    @staticmethod
    def _embedding_table(dimension: int) -> Any:
        if dimension == 64:
            return memory_embeddings
        if dimension == 384:
            return memory_embeddings_semantic
        raise ValueError(f"unsupported embedding dimension: {dimension}")

    @staticmethod
    def _version_values(version: MemoryVersion) -> dict[str, object]:
        return {
            "memory_id": version.memory_id,
            "tenant_id": current_tenant_or_none(),
            "version": version.version,
            "memory_type": version.memory_type.value,
            "content": version.content,
            "importance": version.importance,
            "confidence": version.confidence,
            "state": version.state.value,
            "space": version.space,
            "occurred_at": version.occurred_at,
            "provenance": _provenance_to_json(version.provenance),
            "changed_at": version.changed_at,
            "change_reason": version.change_reason,
        }

    @staticmethod
    def _relation_from_row(row: Any) -> Relation:
        mapping = row._mapping
        return Relation(
            source_id=mapping["source_id"],
            target_id=mapping["target_id"],
            relation_type=RelationType(mapping["relation_type"]),
            owner_id=mapping["owner_id"],
            created_at=mapping["created_at"],
        )

    @staticmethod
    def _version_from_row(row: Any) -> MemoryVersion:
        mapping = row._mapping
        return MemoryVersion(
            memory_id=mapping["memory_id"],
            version=mapping["version"],
            memory_type=MemoryType(mapping["memory_type"]),
            content=mapping["content"],
            importance=mapping["importance"],
            confidence=mapping["confidence"],
            state=MemoryState(mapping["state"]),
            space=mapping["space"],
            occurred_at=mapping["occurred_at"],
            provenance=_provenance_from_json(mapping["provenance"]),
            changed_at=mapping["changed_at"],
            change_reason=mapping["change_reason"],
        )


class PostgresMemoryAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._memories = PostgresMemoryRepository(session)

    async def export_memories(
        self, *, owner_id: str, include_embeddings: bool
    ) -> Sequence[MemoryExportRecord]:
        result = await self._session.execute(
            select(memories.c.id)
            .where(memories.c.owner_id == owner_id)
            .order_by(memories.c.id.asc())
        )
        records: list[MemoryExportRecord] = []
        for row in result:
            record = await self.export_memory(
                owner_id=owner_id,
                memory_id=row._mapping["id"],
                include_embeddings=include_embeddings,
            )
            if record is not None:
                records.append(record)
        return tuple(records)

    async def export_memory(
        self, *, owner_id: str, memory_id: UUID, include_embeddings: bool
    ) -> MemoryExportRecord | None:
        result = await self._session.execute(
            select(memories).where(memories.c.owner_id == owner_id, memories.c.id == memory_id)
        )
        row = result.first()
        if row is None:
            return None
        memory = _memory_from_row(row)
        vector: tuple[float, ...] | None = None
        if include_embeddings:
            if memory.embedding is None:
                raise ValueError("memory must have an embedding descriptor")
            embedding_table = PostgresMemoryRepository._embedding_table(memory.embedding.dimension)
            embedding_result = await self._session.execute(
                select(embedding_table.c.vector).where(embedding_table.c.memory_id == memory_id)
            )
            embedding_row = embedding_result.first()
            if embedding_row is not None:
                vector = tuple(float(item) for item in embedding_row._mapping["vector"])
        return MemoryExportRecord(
            memory=memory,
            history=tuple(await self._memories.history(owner_id=owner_id, memory_id=memory_id)),
            relations=tuple(
                await self._memories.list_relations(owner_id=owner_id, memory_id=memory_id)
            ),
            embedding=vector,
            write_fingerprint=row._mapping["idempotency_fingerprint"],
        )

    async def import_memories(self, *, records: Sequence[MemoryImportRecord]) -> ImportResult:
        imported = 0
        replayed = 0
        relation_keys: set[tuple[str, UUID, UUID, str]] = set()
        for record in records:
            statement = (
                pg_insert(memories)
                .values(
                    PostgresMemoryRepository._memory_values(
                        record.memory, fingerprint=record.write_fingerprint
                    )
                )
                .on_conflict_do_nothing(index_elements=[memories.c.id])
                .returning(memories.c.id)
            )
            try:
                result = await self._session.execute(statement)
            except IntegrityError as exc:
                raise ImportConflictError("import conflicts with existing memory") from exc
            inserted = result.first()
            if inserted is None:
                current = await self._memories.get(
                    owner_id=record.memory.owner_id, memory_id=record.memory.id
                )
                if current != record.memory:
                    raise ImportConflictError("import conflicts with existing memory")
                replayed += 1
                continue
            if record.embedding is None:
                raise ImportConflictError("import embedding is missing")
            try:
                embedding_table = PostgresMemoryRepository._embedding_table(
                    record.memory.embedding.dimension if record.memory.embedding else 0
                )
                await self._session.execute(
                    insert(embedding_table).values(
                        PostgresMemoryRepository._embedding_values(record.memory, record.embedding)
                    )
                )
                await self._session.execute(
                    insert(memory_versions).values(
                        [
                            PostgresMemoryRepository._version_values(snapshot)
                            for snapshot in record.history
                        ]
                    )
                )
            except IntegrityError as exc:
                raise ImportConflictError("import payload could not be stored") from exc
            imported += 1

        for record in records:
            for relation in record.relations:
                relation_key = (
                    relation.owner_id,
                    relation.source_id,
                    relation.target_id,
                    relation.relation_type.value,
                )
                if relation_key in relation_keys:
                    continue
                relation_keys.add(relation_key)
                await self._session.execute(
                    pg_insert(memory_relations)
                    .values(
                        {
                            "owner_id": relation.owner_id,
                            "tenant_id": current_tenant_or_none(),
                            "source_id": relation.source_id,
                            "target_id": relation.target_id,
                            "relation_type": relation.relation_type.value,
                            "created_at": relation.created_at,
                        }
                    )
                    .on_conflict_do_nothing(
                        index_elements=[
                            memory_relations.c.owner_id,
                            memory_relations.c.source_id,
                            memory_relations.c.target_id,
                            memory_relations.c.relation_type,
                        ]
                    )
                )
        return ImportResult(imported=imported, replayed=replayed)


class PostgresUnitOfWork:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], *, community_mode: bool
    ) -> None:
        self._session_factory = session_factory
        self._community_mode = community_mode
        self._session: AsyncSession | None = None
        self.memories: PostgresMemoryRepository
        self.idempotency: PostgresIdempotencyRepository
        self.admin: PostgresMemoryAdminRepository

    async def __aenter__(self) -> PostgresUnitOfWork:
        self._session = self._session_factory()
        await self._session.begin()
        if self._community_mode:
            await self._session.execute(text("SELECT set_config('app.community_mode', '1', true)"))
        else:
            await set_tenant_context(self._session, current_tenant())
        self.memories = PostgresMemoryRepository(self._session)
        self.idempotency = PostgresIdempotencyRepository(self._session)
        self.admin = PostgresMemoryAdminRepository(self._session)
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()


class PostgresUnitOfWorkFactory:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], *, community_mode: bool
    ) -> None:
        self._session_factory = session_factory
        self._community_mode = community_mode

    def __call__(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self._session_factory, community_mode=self._community_mode)


def create_postgres_uow_factory(settings: OMPSettings) -> tuple[PostgresUnitOfWorkFactory, object]:
    """Build a factory and engine; callers own engine disposal."""

    engine = create_async_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresUnitOfWorkFactory(
        session_factory, community_mode=settings.environment != "cloud"
    ), engine
