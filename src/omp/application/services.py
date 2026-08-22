"""Use cases for write, search, update, relation and forget semantics."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Any

from omp.domain import (
    CaptureConsent,
    CaptureDisabledError,
    ConnectionRevokedError,
    ConsentMode,
    ConsentRequiredError,
    EmbeddingProfileMismatchError,
    IdempotencyConflictError,
    ImportConflictError,
    InvalidStateTransitionError,
    Memory,
    MemoryState,
    MemoryType,
    NotFoundError,
    Relation,
    RelationType,
    ScopeDeniedError,
    SpaceForbiddenError,
    ValidationError,
    VersionConflictError,
    utc_now,
)
from omp.domain.types import ensure_aware, validate_owner_id

from .models import (
    CaptureMemoryCommand,
    CaptureMemoryResult,
    ConfirmCandidateCommand,
    DiscardCandidateCommand,
    DiscardResult,
    ForgetMemoryCommand,
    ForgetMemoryResult,
    ImportResult,
    InboxResult,
    ListInboxCommand,
    MemoryExportRecord,
    MemoryImportRecord,
    PinMemoryCommand,
    RecallMemoryCommand,
    RecallResult,
    RelateMemoriesCommand,
    RelateMemoriesResult,
    SearchFilters,
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
                tenant_id=command.tenant_id,
            )
            result = await uow.memories.create(
                memory=memory,
                fingerprint=fingerprint,
                embedding=vector,
            )
            return WriteMemoryResult(memory=result.memory, created=result.created)

    async def capture(self, command: CaptureMemoryCommand) -> CaptureMemoryResult:
        """Capture a consented M1 candidate without granting recall eligibility."""
        self._validate_scope(command.scopes, "memory:write")
        self._validate_scope_value(command.tenant_id, "tenant_id")
        self._validate_scope_value(command.connection_id, "connection_id")
        validate_owner_id(command.owner_id)
        if command.connection_revoked:
            raise ConnectionRevokedError("connection is revoked")
        if command.capture_policy == "disabled":
            raise CaptureDisabledError("capture is disabled for this connection")
        if command.capture_policy not in {"manual", "assisted", "automatic"}:
            raise ValidationError("invalid capture policy")
        if command.capture_policy == "manual" and command.consent.reason_code.value not in {
            "user_requested_memory",
            "user_confirmed_inbox",
        }:
            raise ConsentRequiredError("manual capture requires an explicit user request")
        if command.capture_policy == "automatic" and command.consent.mode != ConsentMode.AUTOMATIC:
            raise ConsentRequiredError("automatic capture requires automatic consent")
        if not command.provenance.source_client or not command.provenance.source_type:
            raise ValidationError("M1 capture requires source_client and source_type")
        fingerprint = _digest(
            {
                "tenant_id": command.tenant_id,
                "connection_id": command.connection_id,
                "content": command.content,
                "type": command.memory_type.value,
                "space": command.space,
                "importance": command.importance,
                "confidence": command.confidence,
                "provenance": _canonical_provenance(command.provenance),
                "consent": _canonical_consent(command.consent),
            }
        )
        async with self._uow_factory() as uow:
            prior = await uow.memories.find_by_idempotency_key(
                owner_id=command.owner_id, idempotency_key=command.idempotency_key
            )
            if prior is not None:
                if prior.fingerprint != fingerprint:
                    raise IdempotencyConflictError(
                        "idempotency_key was already used for another capture"
                    )
                return CaptureMemoryResult(memory=prior.memory, created=False)
            vector = await self._embedding_provider.embed(command.content)
            self._validate_vector(vector)
            memory = Memory.create(
                owner_id=command.owner_id,
                tenant_id=command.tenant_id,
                content=command.content,
                memory_type=command.memory_type,
                importance=command.importance,
                confidence=command.confidence,
                provenance=command.provenance,
                capture_consent=command.consent,
                space=command.space,
                embedding=self._embedding_provider.profile.descriptor(),
                idempotency_key=command.idempotency_key,
                initial_state=MemoryState.CANDIDATE,
                now=ensure_aware(self._clock(), "now"),
            )
            result = await uow.memories.create(
                memory=memory, fingerprint=fingerprint, embedding=vector
            )
            return CaptureMemoryResult(memory=result.memory, created=result.created)

    async def list_inbox(self, command: ListInboxCommand) -> InboxResult:
        self._validate_scope(command.scopes, "memory:read")
        self._validate_scope_value(command.tenant_id, "tenant_id")
        validate_owner_id(command.owner_id)
        if command.connection_revoked:
            raise ConnectionRevokedError("connection is revoked")
        if not 1 <= command.limit <= 100:
            raise ValidationError("limit must be between 1 and 100")
        async with self._uow_factory() as uow:
            candidates = await uow.memories.list_candidates(
                owner_id=command.owner_id,
                tenant_id=command.tenant_id,
                space=command.space,
                limit=command.limit + 1,
            )
        next_cursor = str(command.limit) if len(candidates) > command.limit else None
        return InboxResult(candidates=tuple(candidates[: command.limit]), next_cursor=next_cursor)

    async def confirm_candidate(self, command: ConfirmCandidateCommand) -> Memory:
        self._validate_scope(command.scopes, "memory:write")
        self._validate_mutation_scope(
            command.tenant_id, command.owner_id, command.connection_revoked
        )
        fingerprint = _digest(
            {
                "memory_id": str(command.memory_id),
                "expected_version": command.expected_version,
                "content": command.content,
                "type": command.memory_type.value if command.memory_type else None,
                "space": command.space,
                "reason": command.actor_reason,
            }
        )
        async with self._uow_factory() as uow:
            claim = await self._claim(
                uow, command.owner_id, "confirm", command.idempotency_key, fingerprint
            )
            if claim.replay:
                replay = await uow.memories.get_version(
                    owner_id=command.owner_id,
                    tenant_id=command.tenant_id,
                    memory_id=claim.memory_id or command.memory_id,
                    version=claim.result_version or command.expected_version,
                )
                if replay is None:
                    raise NotFoundError("memory was not found")
                return replay
            current = await uow.memories.get(
                owner_id=command.owner_id, tenant_id=command.tenant_id, memory_id=command.memory_id
            )
            if current is None:
                raise NotFoundError("memory was not found")
            if current.version != command.expected_version:
                raise VersionConflictError("memory version has changed")
            if current.state not in {MemoryState.CANDIDATE, MemoryState.STALE}:
                raise InvalidStateTransitionError(
                    "only a candidate or stale memory can be confirmed"
                )
            evolve_kwargs: dict[str, object] = {
                "now": ensure_aware(self._clock(), "now"),
                "state": MemoryState.CONFIRMED,
                "change_reason": command.actor_reason,
                "embedding": self._embedding_provider.profile.descriptor(),
            }
            if command.content is not None:
                evolve_kwargs["content"] = command.content
            if command.memory_type is not None:
                evolve_kwargs["memory_type"] = command.memory_type
            if command.space is not None:
                evolve_kwargs["space"] = command.space
            updated = current.evolve(**evolve_kwargs)  # type: ignore[arg-type]
            vector = await self._embedding_provider.embed(updated.content)
            self._validate_vector(vector)
            persisted = await uow.memories.update(
                memory=updated,
                expected_version=command.expected_version,
                version_snapshot=updated.snapshot(change_reason=command.actor_reason),
                embedding=vector,
            )
            await uow.idempotency.complete(
                claim=claim,
                memory_id=persisted.id,
                result_version=persisted.version,
                result_status="confirmed",
            )
            return persisted

    async def pin(self, command: PinMemoryCommand) -> Memory:
        self._validate_scope(command.scopes, "memory:write")
        self._validate_mutation_scope(
            command.tenant_id, command.owner_id, command.connection_revoked
        )
        fingerprint = _digest(
            {
                "memory_id": str(command.memory_id),
                "expected_version": command.expected_version,
                "pinned": command.pinned,
            }
        )
        target_state = MemoryState.PINNED if command.pinned else MemoryState.CONFIRMED
        async with self._uow_factory() as uow:
            claim = await self._claim(
                uow, command.owner_id, "pin", command.idempotency_key, fingerprint
            )
            if claim.replay:
                replay = await uow.memories.get_version(
                    owner_id=command.owner_id,
                    tenant_id=command.tenant_id,
                    memory_id=claim.memory_id or command.memory_id,
                    version=claim.result_version or command.expected_version,
                )
                if replay is None:
                    raise NotFoundError("memory was not found")
                return replay
            current = await uow.memories.get(
                owner_id=command.owner_id, tenant_id=command.tenant_id, memory_id=command.memory_id
            )
            if current is None:
                raise NotFoundError("memory was not found")
            if current.version != command.expected_version:
                raise VersionConflictError("memory version has changed")
            if current.state not in {MemoryState.CONFIRMED, MemoryState.PINNED}:
                raise InvalidStateTransitionError("only confirmed memories can be pinned")
            if current.state == target_state:
                await uow.idempotency.complete(
                    claim=claim,
                    memory_id=current.id,
                    result_version=current.version,
                    result_status=target_state.value,
                )
                return current
            updated = current.evolve(
                now=ensure_aware(self._clock(), "now"),
                state=target_state,
                change_reason="pinned" if command.pinned else "unpinned",
            )
            vector = await self._embedding_provider.embed(updated.content)
            self._validate_vector(vector)
            persisted = await uow.memories.update(
                memory=updated,
                expected_version=current.version,
                version_snapshot=updated.snapshot(change_reason=updated.state.value),
                embedding=vector,
            )
            await uow.idempotency.complete(
                claim=claim,
                memory_id=persisted.id,
                result_version=persisted.version,
                result_status=target_state.value,
            )
            return persisted

    async def discard_candidate(self, command: DiscardCandidateCommand) -> DiscardResult:
        self._validate_scope(command.scopes, "memory:delete")
        self._validate_mutation_scope(
            command.tenant_id, command.owner_id, command.connection_revoked
        )
        fingerprint = _digest(
            {
                "memory_id": str(command.memory_id),
                "expected_version": command.expected_version,
                "reason": command.reason_code,
            }
        )
        async with self._uow_factory() as uow:
            claim = await self._claim(
                uow, command.owner_id, "discard", command.idempotency_key, fingerprint
            )
            if claim.replay:
                return DiscardResult(command.memory_id, claim.result_status == "forgotten")
            current = await uow.memories.get(
                owner_id=command.owner_id, tenant_id=command.tenant_id, memory_id=command.memory_id
            )
            if current is None:
                raise NotFoundError("memory was not found")
            if current.version != command.expected_version:
                raise VersionConflictError("memory version has changed")
            if current.state != MemoryState.CANDIDATE:
                raise InvalidStateTransitionError("only a candidate can be discarded")
            forgotten = await uow.memories.forget(
                owner_id=command.owner_id, tenant_id=command.tenant_id, memory_id=command.memory_id
            )
            await uow.idempotency.complete(
                claim=claim,
                memory_id=command.memory_id,
                result_version=None,
                result_status="forgotten" if forgotten else "already_absent",
            )
            return DiscardResult(command.memory_id, forgotten)

    async def recall(self, command: RecallMemoryCommand) -> RecallResult:
        self._validate_scope(command.scopes, "memory:read")
        self._validate_scope_value(command.tenant_id, "tenant_id")
        validate_owner_id(command.owner_id)
        if command.connection_revoked:
            raise ConnectionRevokedError("connection is revoked")
        if not command.query.strip():
            raise ValidationError("query must be non-empty")
        if not 1 <= command.limit <= 100 or not 1 <= command.candidate_limit <= 500:
            raise ValidationError("invalid recall limits")
        if not 0 <= command.threshold <= 1:
            raise ValidationError("threshold must be between 0 and 1")
        requested_spaces = command.include_spaces or (command.context_space,)
        if any(space is None for space in requested_spaces):
            requested_spaces = tuple(space for space in requested_spaces if space is not None) or (
                None,
            )
        for space in requested_spaces:
            if space != command.context_space and not command.space_policy.allows(
                space, context_space=command.context_space
            ):
                raise SpaceForbiddenError("requested space is not allowed by connection policy")
        query_vector = await self._embedding_provider.embed(command.query, query=True)
        self._validate_vector(query_vector)
        filters_base = command.memory_types
        async with self._uow_factory() as uow:
            candidates = []
            for space in requested_spaces:
                filters = SearchFilters(
                    states=command.states, memory_types=filters_base, space=space
                )
                candidates.extend(
                    await uow.memories.search_candidates(
                        owner_id=command.owner_id,
                        tenant_id=command.tenant_id,
                        query_embedding=query_vector,
                        profile=self._embedding_provider.profile,
                        filters=filters,
                        limit=command.candidate_limit,
                    )
                )
        ranked: list[SearchMemoryItem] = []
        seen: set[Any] = set()
        for candidate in candidates:
            if candidate.memory.id in seen or (
                candidate.memory.memory_type == MemoryType.MENTAL_NOTE
                and not command.allow_mental_notes
            ):
                continue
            seen.add(candidate.memory.id)
            similarity = max(0.0, min(1.0, candidate.similarity))
            if similarity < command.threshold:
                continue
            reason = (
                "explicit_cross_space_semantic_match"
                if candidate.memory.space != command.context_space
                else "same_space_semantic_match"
            )
            ranked.append(
                SearchMemoryItem(
                    memory=candidate.memory,
                    score=round(
                        (0.75 * similarity)
                        + (0.15 * candidate.memory.importance)
                        + (0.10 * candidate.memory.confidence),
                        6,
                    ),
                    similarity=round(similarity, 6),
                    profile_id=self._embedding_provider.profile.id,
                    profile_version=self._embedding_provider.profile.version,
                    reason_retrieved=reason,
                )
            )
        ranked.sort(key=lambda item: (-item.score, -item.similarity, str(item.memory.id)))
        items = tuple(ranked[: command.limit])
        profile = self._embedding_provider.profile
        return RecallResult(
            items=items, count=len(items), profile_id=profile.id, profile_version=profile.version
        )

    @staticmethod
    def _validate_scope(scopes: frozenset[str], required: str) -> None:
        if required not in scopes:
            raise ScopeDeniedError("connection scope does not permit this operation")

    @staticmethod
    def _validate_scope_value(value: str, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field_name} must be non-empty")

    @staticmethod
    def _validate_mutation_scope(tenant_id: str, owner_id: str, revoked: bool) -> None:
        MemoryApplicationService._validate_scope_value(tenant_id, "tenant_id")
        validate_owner_id(owner_id)
        if revoked:
            raise ConnectionRevokedError("connection is revoked")

    @staticmethod
    async def _claim(uow: UnitOfWork, owner_id: str, operation: str, key: str, fingerprint: str):
        return await uow.idempotency.claim(
            owner_id=owner_id,
            operation_type=IdempotencyOperationType(operation),
            idempotency_key=key,
            fingerprint=fingerprint,
        )

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
                if current is None and await uow.admin.is_tombstoned(
                    owner_id=owner_id, memory_id=record.memory.id, tenant_id=record.memory.tenant_id
                ):
                    from omp.domain import RestoreBlockedByTombstoneError

                    raise RestoreBlockedByTombstoneError("memory restore is blocked by a tombstone")
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
            # The selected runtime profile owns the new vector.  The storage
            # adapter keeps the previous profile in its parallel table, so a
            # controlled cutover or rollback never mixes dimensions in one row.
            kwargs["embedding"] = self._embedding_provider.profile.descriptor()
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
        query_vector = await self._embedding_provider.embed(command.query, query=True)
        self._validate_vector(query_vector)
        profile = self._embedding_provider.profile
        states = command.filters.states
        if MemoryState.ACTIVE in states:
            # v0's active wire alias includes every M1 recall-eligible state.
            states = frozenset(states | {MemoryState.CONFIRMED, MemoryState.PINNED})
        filters = replace(command.filters, states=states)
        async with self._uow_factory() as uow:
            candidates = await uow.memories.search_candidates(
                owner_id=command.owner_id,
                query_embedding=query_vector,
                profile=profile,
                filters=filters,
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
                owner_id=command.owner_id, tenant_id=command.tenant_id, memory_id=command.memory_id
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
        "source_client": provenance.source_client,
        "source_connection_id": provenance.source_connection_id,
        "conversation_id": provenance.conversation_id,
        "message_id": provenance.message_id,
        "captured_at": provenance.captured_at.isoformat(),
        "evidence": list(provenance.evidence),
    }


def _canonical_consent(consent: CaptureConsent) -> dict[str, object]:
    return {
        "mode": consent.mode.value,
        "consent_id": consent.consent_id,
        "reason_code": consent.reason_code.value,
        "policy_version": consent.policy_version,
        "granted_at": consent.granted_at.isoformat(),
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
