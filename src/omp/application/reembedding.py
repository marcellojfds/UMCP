"""Resumable, owner-scoped semantic re-embedding workflow."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from omp.domain.types import validate_owner_id

from .ports import EmbeddingProvider, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class ReembeddingReport:
    owner_id: str
    profile_id: str
    profile_version: str
    dry_run: bool
    cutover: bool
    eligible: int
    completed: int
    stale: int
    failed: int
    last_memory_id: UUID | None
    activated: int


class EmbeddingReembeddingJob:
    """Materialize a parallel profile without changing memory lifecycle state."""

    def __init__(self, *, uow_factory: UnitOfWorkFactory, embedding_provider: EmbeddingProvider):
        self._uow_factory = uow_factory
        self._provider = embedding_provider

    async def run(
        self,
        *,
        owner_id: str,
        batch_size: int = 100,
        resume_after: UUID | None = None,
        dry_run: bool = False,
        cutover: bool = False,
    ) -> ReembeddingReport:
        validate_owner_id(owner_id)
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        if self._provider.profile.dimension != 384:
            raise ValueError("the re-embedding job requires a 384-dimensional provider")

        eligible = completed = stale = failed = 0
        cursor = resume_after
        while True:
            async with self._uow_factory() as uow:
                candidates = await uow.memories.list_for_reembedding(
                    owner_id=owner_id, after_memory_id=cursor, limit=batch_size
                )
                if not candidates:
                    break
                eligible += len(candidates)
                if not dry_run:
                    for memory in candidates:
                        try:
                            vector = await self._provider.embed(memory.content)
                            if len(vector) != self._provider.profile.dimension:
                                raise ValueError("provider returned an unexpected dimension")
                            if not await uow.memories.upsert_embedding_profile(
                                memory_id=memory.id,
                                expected_version=memory.version,
                                profile=self._provider.profile,
                                embedding=vector,
                            ):
                                stale += 1
                            else:
                                completed += 1
                        except Exception:
                            failed += 1
                cursor = candidates[-1].id
            if len(candidates) < batch_size:
                break

        activated = 0
        if cutover and not dry_run:
            async with self._uow_factory() as uow:
                activated = await uow.memories.cutover_embedding_profile(
                    owner_id=owner_id, profile=self._provider.profile
                )
        async with self._uow_factory() as uow:
            total, _covered = await uow.memories.semantic_coverage(
                owner_id=owner_id, profile=self._provider.profile
            )
        return ReembeddingReport(
            owner_id=owner_id,
            profile_id=self._provider.profile.id,
            profile_version=self._provider.profile.version,
            dry_run=dry_run,
            cutover=cutover,
            eligible=total if dry_run else eligible,
            completed=completed,
            stale=stale,
            failed=failed,
            last_memory_id=cursor,
            activated=activated,
        )
