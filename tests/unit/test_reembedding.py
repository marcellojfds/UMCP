from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest

from omp.application.ports import EmbeddingProfile
from omp.application.reembedding import EmbeddingReembeddingJob


class StaticProvider:
    profile = EmbeddingProfile("semantic", "test-v1", 384)

    async def embed(self, text: str, *, query: bool = False) -> tuple[float, ...]:
        return (1.0,) + (0.0,) * 383


class FakeMemoryRepository:
    def __init__(self) -> None:
        self.records = [
            SimpleNamespace(id=UUID(int=index + 1), version=1, content=f"memory-{index}")
            for index in range(3)
        ]
        self.vectors: dict[UUID, tuple[float, ...]] = {}
        self.current_versions = {record.id: record.version for record in self.records}
        self.cutovers = 0

    async def list_for_reembedding(
        self, *, owner_id: str, after_memory_id: UUID | None, limit: int
    ) -> list[SimpleNamespace]:
        records = [
            record
            for record in self.records
            if after_memory_id is None or record.id > after_memory_id
        ]
        return records[:limit]

    async def upsert_embedding_profile(
        self,
        *,
        memory_id: UUID,
        expected_version: int,
        profile: EmbeddingProfile,
        embedding: tuple[float, ...],
    ) -> bool:
        if self.current_versions[memory_id] != expected_version:
            return False
        self.vectors[memory_id] = embedding
        return True

    async def semantic_coverage(
        self, *, owner_id: str, profile: EmbeddingProfile
    ) -> tuple[int, int]:
        return len(self.records), len(self.vectors)

    async def cutover_embedding_profile(self, *, owner_id: str, profile: EmbeddingProfile) -> int:
        if len(self.vectors) != len(self.records):
            raise RuntimeError("semantic embedding coverage is incomplete")
        self.cutovers += 1
        return len(self.records)


class FakeUnitOfWork:
    def __init__(self, repository: FakeMemoryRepository) -> None:
        self.memories = repository

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


@pytest.mark.asyncio
async def test_reembedding_is_batched_resumable_and_cutover_requires_coverage() -> None:
    repository = FakeMemoryRepository()

    @asynccontextmanager
    async def factory() -> object:
        yield FakeUnitOfWork(repository)

    job = EmbeddingReembeddingJob(uow_factory=factory, embedding_provider=StaticProvider())
    report = await job.run(owner_id="owner-a", batch_size=2, cutover=True)

    assert report.eligible == 3
    assert report.completed == 3
    assert report.stale == 0
    assert report.failed == 0
    assert report.activated == 3
    assert repository.cutovers == 1
    assert len(repository.vectors) == 3


@pytest.mark.asyncio
async def test_reembedding_dry_run_does_not_write_vectors() -> None:
    repository = FakeMemoryRepository()

    @asynccontextmanager
    async def factory() -> object:
        yield FakeUnitOfWork(repository)

    job = EmbeddingReembeddingJob(uow_factory=factory, embedding_provider=StaticProvider())
    report = await job.run(owner_id="owner-a", dry_run=True)

    assert report.eligible == 3
    assert report.completed == 0
    assert report.activated == 0
    assert repository.vectors == {}
