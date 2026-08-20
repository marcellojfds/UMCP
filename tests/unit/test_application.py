import asyncio
from dataclasses import replace

import pytest

from omp.adapters.embeddings import HashEmbeddingProvider
from omp.application.fakes import InMemoryUnitOfWorkFactory
from omp.application.models import (
    ForgetMemoryCommand,
    RelateMemoriesCommand,
    SearchMemoryCommand,
    UpdateMemoryCommand,
    WriteMemoryCommand,
)
from omp.application.services import MemoryApplicationService
from omp.domain import (
    EmbeddingProfileMismatchError,
    IdempotencyConflictError,
    ImportConflictError,
    MemoryState,
    MemoryType,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from tests.fixtures.domain import provenance


def service() -> MemoryApplicationService:
    return MemoryApplicationService(
        uow_factory=InMemoryUnitOfWorkFactory(),
        embedding_provider=HashEmbeddingProvider(),
    )


def command(
    owner_id: str, *, key: str | None = None, content: str = "market density"
) -> WriteMemoryCommand:
    return WriteMemoryCommand(
        owner_id=owner_id,
        content=content,
        memory_type=MemoryType.INSIGHT,
        provenance=provenance(owner_id),
        importance=0.9,
        confidence=0.9,
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_cross_owner_isolation_and_negative_abstention() -> None:
    app = service()
    first = await app.write(command("owner-a", content="market density strategy"))
    await app.write(command("owner-b", content="market density strategy"))
    found = await app.search(
        SearchMemoryCommand(owner_id="owner-a", query="market density strategy")
    )
    assert [item.memory.id for item in found.items] == [first.memory.id]
    negative = await app.search(
        SearchMemoryCommand(owner_id="owner-a", query="quantum cooking unrelated", threshold=0.99)
    )
    assert negative.items == ()


@pytest.mark.asyncio
async def test_idempotency_is_scoped_to_owner_and_replay_is_stable() -> None:
    app = service()
    first = await app.write(command("owner-a", key="same-key"))
    replay = await app.write(command("owner-a", key="same-key"))
    other_owner = await app.write(command("owner-b", key="same-key"))
    assert first.created is True
    assert replay.created is False
    assert replay.memory.id == first.memory.id
    assert other_owner.created is True


@pytest.mark.asyncio
async def test_update_requires_expected_version_and_forget_is_idempotent() -> None:
    app = service()
    created = await app.write(command("owner-a"))
    updated = await app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=created.memory.id,
            expected_version=1,
            content="updated market density insight",
        )
    )
    assert updated.version == 2
    with pytest.raises(VersionConflictError):
        await app.update(
            UpdateMemoryCommand(
                owner_id="owner-a",
                memory_id=created.memory.id,
                expected_version=1,
                content="stale write",
            )
        )
    forgotten = await app.forget(ForgetMemoryCommand("owner-a", created.memory.id))
    repeated = await app.forget(ForgetMemoryCommand("owner-a", created.memory.id))
    assert forgotten.forgotten is True
    assert repeated.forgotten is False
    with pytest.raises(NotFoundError):
        await app.update(
            UpdateMemoryCommand(owner_id="owner-a", memory_id=created.memory.id, expected_version=2)
        )


@pytest.mark.asyncio
async def test_default_search_excludes_archived_memories() -> None:
    app = service()
    created = await app.write(command("owner-a"))
    await app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=created.memory.id,
            expected_version=1,
            state=MemoryState.ARCHIVED,
        )
    )
    result = await app.search(SearchMemoryCommand(owner_id="owner-a", query="market density"))
    assert result.items == ()


@pytest.mark.asyncio
async def test_two_concurrent_writes_with_same_key_create_one_memory() -> None:
    app = service()
    results = await asyncio.gather(
        app.write(command("owner-a", key="race")),
        app.write(command("owner-a", key="race")),
    )
    assert len({result.memory.id for result in results}) == 1
    assert sorted(result.created for result in results) == [False, True]


@pytest.mark.asyncio
async def test_relations_are_owner_scoped_and_forget_cascades_them() -> None:
    app = service()
    source = await app.write(command("owner-a", content="source memory"))
    target = await app.write(command("owner-a", content="target memory"))
    relation = await app.relate(
        RelateMemoriesCommand(
            owner_id="owner-a",
            source_memory_id=source.memory.id,
            target_memory_id=target.memory.id,
            relation_type="related_to",
        )
    )
    assert relation.relation.owner_id == "owner-a"
    with pytest.raises(NotFoundError):
        await app.relate(
            RelateMemoriesCommand(
                owner_id="owner-b",
                source_memory_id=source.memory.id,
                target_memory_id=target.memory.id,
                relation_type="related_to",
            )
        )
    await app.forget(ForgetMemoryCommand("owner-a", source.memory.id))
    async with app._uow_factory() as uow:  # contract-level inspection of the fake
        assert (
            await uow.memories.list_relations(owner_id="owner-a", memory_id=target.memory.id) == ()
        )


@pytest.mark.asyncio
async def test_update_idempotency_replay_returns_original_snapshot() -> None:
    factory = InMemoryUnitOfWorkFactory()
    app = MemoryApplicationService(
        uow_factory=factory,
        embedding_provider=HashEmbeddingProvider(),
    )
    created = await app.write(command("owner-a"))
    update = UpdateMemoryCommand(
        owner_id="owner-a",
        memory_id=created.memory.id,
        expected_version=1,
        content="first update",
        idempotency_key="update-1",
    )
    first, replay = await asyncio.gather(app.update(update), app.update(update))
    assert first.version == replay.version == 2
    assert first.content == replay.content == "first update"
    changed = await app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=created.memory.id,
            expected_version=2,
            content="second update",
        )
    )
    assert changed.version == 3
    replay_after_change = await app.update(update)
    assert replay_after_change.version == 2
    assert replay_after_change.content == "first update"


@pytest.mark.asyncio
async def test_update_same_key_with_different_payload_conflicts() -> None:
    app = service()
    created = await app.write(command("owner-a"))
    await app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=created.memory.id,
            expected_version=1,
            content="first update",
            idempotency_key="update-1",
        )
    )
    with pytest.raises(IdempotencyConflictError):
        await app.update(
            UpdateMemoryCommand(
                owner_id="owner-a",
                memory_id=created.memory.id,
                expected_version=1,
                content="different update",
                idempotency_key="update-1",
            )
        )


@pytest.mark.asyncio
async def test_forget_key_replay_and_operation_type_are_independent() -> None:
    app = service()
    created = await app.write(command("owner-a"))
    forgotten = await app.forget(
        ForgetMemoryCommand("owner-a", created.memory.id, idempotency_key="same")
    )
    replay = await app.forget(
        ForgetMemoryCommand("owner-a", created.memory.id, idempotency_key="same")
    )
    assert forgotten.forgotten is True
    assert replay.forgotten is False

    other = await app.write(command("owner-a", key="same"))
    assert other.created is True


class WrongDimensionProvider(HashEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.bad = False

    async def embed(self, text: str) -> tuple[float, ...]:
        if self.bad:
            return (0.0, 1.0, 0.0)
        return tuple(await super().embed(text))


@pytest.mark.asyncio
async def test_failed_update_rolls_back_idempotency_claim() -> None:
    factory = InMemoryUnitOfWorkFactory()
    provider = WrongDimensionProvider()
    app = MemoryApplicationService(uow_factory=factory, embedding_provider=provider)
    created = await app.write(command("owner-a"))
    provider.bad = True
    with pytest.raises(ValidationError):
        await app.update(
            UpdateMemoryCommand(
                owner_id="owner-a",
                memory_id=created.memory.id,
                expected_version=1,
                content="retryable update",
                idempotency_key="retry",
            )
        )

    provider.bad = False
    retried = await app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=created.memory.id,
            expected_version=1,
            content="retryable update",
            idempotency_key="retry",
        )
    )
    assert retried.version == 2


@pytest.mark.asyncio
async def test_export_import_round_trip_is_owner_scoped_and_idempotent() -> None:
    source = service()
    first = await source.write(command("owner-a", content="exported source"))
    second = await source.write(command("owner-a", content="exported target"))
    await source.relate(
        RelateMemoriesCommand("owner-a", first.memory.id, second.memory.id, "related_to")
    )
    await source.update(
        UpdateMemoryCommand("owner-a", first.memory.id, expected_version=1, content="exported v2")
    )
    records = await source.export_memories(owner_id="owner-a")
    assert len(records) == 2
    assert all(record.embedding is None for record in records)
    assert all(record.history for record in records)

    target = service()
    result = await target.import_memories(owner_id="owner-a", records=records)
    replay = await target.import_memories(owner_id="owner-a", records=records)
    assert result.imported == 2
    assert result.replayed == 0
    assert replay.imported == 0
    assert replay.replayed == 2
    async with target._uow_factory() as uow:
        assert (
            len(await uow.memories.list_relations(owner_id="owner-a", memory_id=first.memory.id))
            == 1
        )
        assert len(await uow.memories.history(owner_id="owner-a", memory_id=first.memory.id)) == 2


@pytest.mark.asyncio
async def test_import_validates_all_records_before_mutating_and_conflicts_stably() -> None:
    source = service()
    created = await source.write(command("owner-a", content="canonical export"))
    records = await source.export_memories(owner_id="owner-a")
    target = service()
    invalid = replace(records[0], memory=replace(records[0].memory, owner_id="owner-b"))
    with pytest.raises(ValidationError):
        await target.import_memories(owner_id="owner-a", records=(records[0], invalid))
    async with target._uow_factory() as uow:
        assert await uow.memories.get(owner_id="owner-a", memory_id=created.memory.id) is None

    await target.import_memories(owner_id="owner-a", records=records)
    divergent = replace(records[0], memory=replace(records[0].memory, content="divergent"))
    with pytest.raises(ImportConflictError):
        await target.import_memories(owner_id="owner-a", records=(divergent,))


@pytest.mark.asyncio
async def test_import_requires_compatible_profile_when_vectors_are_excluded() -> None:
    source = service()
    await source.write(command("owner-a", content="profile-bound export"))
    records = await source.export_memories(owner_id="owner-a")
    target_factory = InMemoryUnitOfWorkFactory()
    target = MemoryApplicationService(
        uow_factory=target_factory,
        embedding_provider=HashEmbeddingProvider(version="v2"),
    )
    with pytest.raises(EmbeddingProfileMismatchError):
        await target.import_memories(owner_id="owner-a", records=records)
