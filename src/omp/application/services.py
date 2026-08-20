"""Use cases for write, search, update, relation and forget semantics."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Any

from omp.domain import (
    EmbeddingProfileMismatchError,
    IdempotencyConflictError,
    ImportConflictError,
    Memory,
    NotFoundError,
    Relation,
    RelationType,
    ValidationError,
    VersionConflictError,
    utc_now,
)
from omp.domain.types import MemoryState, ensure_aware, validate_owner_id

from .models import (
    ForgetMemoryCommand,
    ForgetMemoryResult,
    ImportResult,
    MemoryExportRecord,
    MemoryImportRecord,
    RelateMemoriesCommand,
    RelateMemoriesResult,
    SearchMemoryCommand,
    SearchMemoryItem,
    SearchMemoryResult,
    UpdateMemoryCommand,
    WriteMemoryCommand,
    WriteMemoryResult,
)
from .ports import (
    Clock,
    EmbeddingProvider,
    IdempotencyOperationType,
    UnitOfWork,
)


class MemoryApplicationService:
    """Transport-neutral application facade.

    The service is deliberately async so MCP, HTTP and CLI adapters can share
    exactly the same concurrency and error semantics.
    """

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        embedding_provider: EmbeddingProvider,
        clock: Clock = utc_now,
    ) -> None:
        self._uow_factory = uow_factory
        self._embedding_provider = embedding_provider
        self._clock = clock

    async def write(self, command: WriteMemoryCommand) -> WriteMemoryResult:
        validate_owner_id(command.owner_id)
        timestamp = ensure_aware(self._clock(), "now")
        fingerprint = self._fingerprint(command)
        async with self._uow_factory() as uow:
            if command.idempotency_key:
                prior = await uow.memories.find_by_idempotency_key(
                    owner_id=command.owner_id,
                    idempotency_key=command.idempotency_key,
                )
                if prior is not None:
                    if prior.fingerprint != fingerprint:
                        raise IdempotencyConflictError(
                            "idempotency_key was already used for another memory"
                        )
                    return WriteMemoryResult(memory=prior.memory, created=False)
            vector = await self._embedding_provider.embed(command.content)
            self._validate_vector(vector)
            memory = Memory.create(
                owner_id=command.owner_id,
                content=command.content,
                memory_type=command.memory_type,
                importance=command.importance,
                confidence=command.confidence,
                provenance=command.provenance,
                space=command.space,
                occurred_at=command.occurred_at,
                embedding=self._embedding_provider.profile.descriptor(),
                idempotency_key=command.idempotency_key,
                now=timestamp,
            )
            result = await uow.memories.create(
                memory=memory,
                fingerprint=fingerprint,
                embedding=vector,
            )
            return WriteMemoryResult(memory=result.memory, created=result.created)

    async def export_memories(
        self, *, owner_id: str, include_embeddings: bool = False
    ) -> tuple[MemoryExportRecord, ...]:
        """Export one owner's memories in a consistent read transaction."""

        validate_owner_id(owner_id)
        async with self._uow_factory() as uow:
            records = await uow.admin.export_memories(
                owner_id=owner_id, include_embeddings=include_embeddings
            )
        return tuple(records)

    async def import_memories(
        self, *, owner_id: str, records: Sequence[MemoryImportRecord]
    ) -> ImportResult:
        """Validate a complete owner-scoped package before one transaction mutates."""

        validate_owner_id(owner_id)
        incoming = tuple(records)
        incoming_ids: set[Any] = set()
        async with self._uow_factory() as uow:
            for record in incoming:
                self._validate_import_record(owner_id, record, incoming_ids)

            for record in incoming:
                for relation in record.relations:
                    for endpoint in (relation.source_id, relation.target_id):
                        if (
                            endpoint not in incoming_ids
                            and await uow.memories.get(owner_id=owner_id, memory_id=endpoint)
                            is None
                        ):
                            raise NotFoundError("import relation endpoint was not found")

            existing: dict[Any, MemoryExportRecord] = {}
            for record in incoming:
                current = await uow.admin.export_memory(
                    owner_id=owner_id,
                    memory_id=record.memory.id,
                    include_embeddings=True,
                )
                if current is not None:
                    existing[record.memory.id] = current
                    if not _import_records_equivalent(record, current):
                        raise ImportConflictError("import conflicts with existing memory")

            prepared: list[MemoryImportRecord] = []
            for record in incoming:
                if record.memory.id in existing or record.embedding is not None:
                    prepared.append(record)
                    continue
                descriptor = record.memory.embedding
                if (
                    descriptor is None
                    or descriptor != self._embedding_provider.profile.descriptor()
                ):
                    raise EmbeddingProfileMismatchError(
                        "import requires a compatible embedding profile"
                    )
                vector = await self._embedding_provider.embed(record.memory.content)
                self._validate_vector(vector)
                prepared.append(replace(record, embedding=tuple(float(item) for item in vector)))

            return await uow.admin.import_memories(records=tuple(prepared))

    @staticmethod
    def _validate_import_record(
        owner_id: str, record: MemoryImportRecord, incoming_ids: set[Any]
    ) -> None:
        memory = record.memory
        if memory.id in incoming_ids:
            raise ValidationError("import contains duplicate memory IDs")
        incoming_ids.add(memory.id)
        if memory.owner_id != owner_id:
            raise ValidationError("import record owner does not match scope")
        expected_versions = tuple(range(1, memory.version + 1))
        versions = tuple(snapshot.version for snapshot in record.history)
        if versions != expected_versions or any(
            snapshot.memory_id != memory.id for snapshot in record.history
        ):
            raise ValidationError("import history is not a complete version sequence")
        if memory.idempotency_key is not None and record.write_fingerprint is None:
            raise ValidationError("import write fingerprint is required for idempotency keys")
        if record.write_fingerprint is not None:
            if len(record.write_fingerprint) != 64 or any(
                character not in "0123456789abcdef" for character in record.write_fingerprint
            ):
                raise ValidationError("import write fingerprint is invalid")
        if record.embedding is not None:
            if memory.embedding is None or len(record.embedding) != memory.embedding.dimension:
                raise ValidationError("import embedding dimension is invalid")
            if any(not isinstance(value, int | float) for value in record.embedding):
                raise ValidationError("import embedding contains a non-numeric value")
        for relation in record.relations:
            if relation.owner_id != owner_id:
                raise ValidationError("import relation owner does not match scope")

    async def update(self, command: UpdateMemoryCommand) -> Memory:
        validate_owner_id(command.owner_id)
        fingerprint = fingerprint_update_command(command)
        async with self._uow_factory() as uow:
            claim = None
            if command.idempotency_key:
                claim = await uow.idempotency.claim(
                    owner_id=command.owner_id,
                    operation_type=IdempotencyOperationType.UPDATE,
                    idempotency_key=command.idempotency_key,
                    fingerprint=fingerprint,
                )
                if claim.replay:
                    replay = await uow.memories.get_version(
                        owner_id=command.owner_id,
                        memory_id=claim.memory_id or command.memory_id,
                        version=claim.result_version or command.expected_version,
                    )
                    if replay is None:
                        raise NotFoundError("memory was not found")
                    return replay
            current = await uow.memories.get(owner_id=command.owner_id, memory_id=command.memory_id)
            if current is None:
                raise NotFoundError("memory was not found")
            if current.version != command.expected_version:
                raise VersionConflictError(
                    f"expected version {command.expected_version}, "
                    f"current version {current.version}"
                )
            kwargs: dict[str, object] = {"now": ensure_aware(self._clock(), "now")}
            for field_name in (
                "content",
                "memory_type",
                "importance",
                "confidence",
                "state",
                "occurred_at",
                "space",
                "provenance",
            ):
                value = getattr(command, field_name)
                if value is not None:
                    kwargs[field_name] = value
            if command.supersedes_memory_id and command.contradicts_memory_id:
                raise ValidationError("an update cannot supersede and contradict two memories")
            related_id = command.supersedes_memory_id or command.contradicts_memory_id
            if related_id is not None:
                if related_id == current.id:
                    raise ValidationError("a memory cannot relate to itself")
                related = await uow.memories.get(owner_id=command.owner_id, memory_id=related_id)
                if related is None:
                    raise NotFoundError("related memory was not found")
            if command.supersedes_memory_id is not None:
                kwargs["state"] = MemoryState.SUPERSEDED
                kwargs["related_memory_id"] = command.supersedes_memory_id
            elif command.contradicts_memory_id is not None:
                kwargs["state"] = MemoryState.CONTRADICTED
                kwargs["related_memory_id"] = command.contradicts_memory_id
            kwargs["change_reason"] = command.change_reason
            updated = current.evolve(**kwargs)  # type: ignore[arg-type]
            vector = (
                await self._embedding_provider.embed(updated.content)
                if updated.content != current.content
                else await self._embedding_provider.embed(current.content)
            )
            self._validate_vector(vector)
            persisted = await uow.memories.update(
                memory=updated,
                expected_version=command.expected_version,
                version_snapshot=updated.snapshot(change_reason=command.change_reason),
                embedding=vector,
            )
            if command.supersedes_memory_id is not None:
                await uow.memories.add_relation(
                    relation=Relation(
                        source_id=persisted.id,
                        target_id=command.supersedes_memory_id,
                        relation_type=RelationType.SUPERSEDES,
                        owner_id=command.owner_id,
                        created_at=ensure_aware(self._clock(), "now"),
                    )
                )
            elif command.contradicts_memory_id is not None:
                await uow.memories.add_relation(
                    relation=Relation(
                        source_id=persisted.id,
                        target_id=command.contradicts_memory_id,
                        relation_type=RelationType.CONTRADICTS,
                        owner_id=command.owner_id,
                        created_at=ensure_aware(self._clock(), "now"),
                    )
                )
            if claim is not None:
                await uow.idempotency.complete(
                    claim=claim,
                    memory_id=persisted.id,
                    result_version=persisted.version,
                    result_status="updated",
                )
            return persisted

    async def search(self, command: SearchMemoryCommand) -> SearchMemoryResult:
        validate_owner_id(command.owner_id)
        if not command.query.strip():
            raise ValidationError("query must be non-empty")
        if not 1 <= command.limit <= 100:
            raise ValidationError("limit must be between 1 and 100")
        if not 1 <= command.candidate_limit <= 500:
            raise ValidationError("candidate_limit must be between 1 and 500")
        if not 0 <= command.threshold <= 1:
            raise ValidationError("threshold must be between 0 and 1")
        query_vector = await self._embedding_provider.embed(command.query)
        self._validate_vector(query_vector)
        profile = self._embedding_provider.profile
        async with self._uow_factory() as uow:
            candidates = await uow.memories.search_candidates(
                owner_id=command.owner_id,
                query_embedding=query_vector,
                profile=profile,
                filters=command.filters,
                limit=command.candidate_limit,
            )
        ranked: list[SearchMemoryItem] = []
        for candidate in candidates:
            if candidate.profile != profile:
                raise EmbeddingProfileMismatchError(
                    "candidate uses an incompatible embedding profile"
                )
            similarity = max(0.0, min(1.0, candidate.similarity))
            # Importance/confidence rank already relevant candidates; they cannot
            # rescue a semantically irrelevant candidate below the abstention bar.
            if similarity < command.threshold:
                continue
            score = (
                (0.75 * similarity)
                + (0.15 * candidate.memory.importance)
                + (0.10 * candidate.memory.confidence)
            )
            ranked.append(
                SearchMemoryItem(
                    memory=candidate.memory,
                    score=round(score, 6),
                    similarity=round(similarity, 6),
                    profile_id=profile.id,
                    profile_version=profile.version,
                    reason_retrieved=(
                        f"semantic similarity {similarity:.2f}; "
                        f"importance {candidate.memory.importance:.2f}; "
                        f"confidence {candidate.memory.confidence:.2f}"
                    ),
                )
            )
        ranked.sort(key=lambda item: (-item.score, -item.similarity, str(item.memory.id)))
        return SearchMemoryResult(
            items=tuple(ranked[: command.limit]),
            profile_id=profile.id,
            profile_version=profile.version,
        )

    async def forget(self, command: ForgetMemoryCommand) -> ForgetMemoryResult:
        validate_owner_id(command.owner_id)
        fingerprint = fingerprint_forget_command(command)
        async with self._uow_factory() as uow:
            claim = None
            if command.idempotency_key:
                claim = await uow.idempotency.claim(
                    owner_id=command.owner_id,
                    operation_type=IdempotencyOperationType.FORGET,
                    idempotency_key=command.idempotency_key,
                    fingerprint=fingerprint,
                )
                if claim.replay:
                    return ForgetMemoryResult(memory_id=command.memory_id, forgotten=False)
            forgotten = await uow.memories.forget(
                owner_id=command.owner_id, memory_id=command.memory_id
            )
            if claim is not None:
                await uow.idempotency.complete(
                    claim=claim,
                    memory_id=command.memory_id,
                    result_version=None,
                    result_status="forgotten" if forgotten else "already_absent",
                )
        return ForgetMemoryResult(memory_id=command.memory_id, forgotten=forgotten)

    async def relate(self, command: RelateMemoriesCommand) -> RelateMemoriesResult:
        validate_owner_id(command.owner_id)
        try:
            relation_type = RelationType(command.relation_type)
        except ValueError as exc:
            raise ValidationError("unknown relation type") from exc
        if command.source_memory_id == command.target_memory_id:
            raise ValidationError("a memory cannot relate to itself")
        async with self._uow_factory() as uow:
            source = await uow.memories.get(
                owner_id=command.owner_id, memory_id=command.source_memory_id
            )
            target = await uow.memories.get(
                owner_id=command.owner_id, memory_id=command.target_memory_id
            )
            if source is None or target is None:
                raise NotFoundError("both related memories must exist for this owner")
            relation = Relation(
                source_id=source.id,
                target_id=target.id,
                relation_type=relation_type,
                owner_id=command.owner_id,
                created_at=ensure_aware(self._clock(), "now"),
            )
            return RelateMemoriesResult(relation=await uow.memories.add_relation(relation=relation))

    def _validate_vector(self, vector: Sequence[float]) -> None:
        if len(vector) != self._embedding_provider.profile.dimension:
            raise ValidationError("embedding provider returned an unexpected dimension")
        if any(not isinstance(value, int | float) for value in vector):
            raise ValidationError("embedding provider returned a non-numeric vector")

    def _fingerprint(self, command: WriteMemoryCommand) -> str:
        canonical = _canonical_write_command(command)
        return _digest(canonical)


def _canonical_provenance(provenance: Any) -> dict[str, object]:
    return {
        "source_type": provenance.source_type.value,
        "source_id": provenance.source_id,
        "source_model": provenance.source_model,
        "captured_at": provenance.captured_at.isoformat(),
        "evidence": list(provenance.evidence),
    }


def _canonical_write_command(command: WriteMemoryCommand) -> dict[str, object]:
    return {
        "content": command.content,
        "type": command.memory_type.value,
        "importance": command.importance,
        "confidence": command.confidence,
        "space": command.space,
        "occurred_at": command.occurred_at.isoformat() if command.occurred_at else None,
        "provenance": _canonical_provenance(command.provenance),
    }


def fingerprint_update_command(command: UpdateMemoryCommand) -> str:
    return _digest(
        {
            "owner_id": command.owner_id,
            "memory_id": str(command.memory_id),
            "expected_version": command.expected_version,
            "content": command.content,
            "memory_type": command.memory_type.value if command.memory_type else None,
            "importance": command.importance,
            "confidence": command.confidence,
            "state": command.state.value if command.state else None,
            "occurred_at": command.occurred_at.isoformat() if command.occurred_at else None,
            "space": command.space,
            "provenance": (
                _canonical_provenance(command.provenance) if command.provenance else None
            ),
            "supersedes_memory_id": (
                str(command.supersedes_memory_id) if command.supersedes_memory_id else None
            ),
            "contradicts_memory_id": (
                str(command.contradicts_memory_id) if command.contradicts_memory_id else None
            ),
            "change_reason": command.change_reason,
        }
    )


def fingerprint_forget_command(command: ForgetMemoryCommand) -> str:
    return _digest({"owner_id": command.owner_id, "memory_id": str(command.memory_id)})


def _relation_key(relation: Relation) -> tuple[str, str, str, str]:
    return (
        str(relation.source_id),
        str(relation.target_id),
        relation.relation_type.value,
        relation.owner_id,
    )


def _import_records_equivalent(incoming: MemoryImportRecord, current: MemoryExportRecord) -> bool:
    if incoming.memory != current.memory:
        return False
    if incoming.write_fingerprint is not None and (
        incoming.write_fingerprint != current.write_fingerprint
    ):
        return False
    if incoming.history != current.history:
        return False
    if {_relation_key(item) for item in incoming.relations} != {
        _relation_key(item) for item in current.relations
    }:
        return False
    return incoming.embedding is None or incoming.embedding == current.embedding


def _digest(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
