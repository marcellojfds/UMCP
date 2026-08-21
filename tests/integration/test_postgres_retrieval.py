"""Real PostgreSQL 16 + pgvector integration coverage for the core.

The database is disposable by contract. ``OMP_TEST_DATABASE_URL`` takes
precedence; without it, local mode attempts the project's testcontainers
dependency. ``OMP_REQUIRE_POSTGRES_TESTS=1`` turns database unavailability
into an explicit failure instead of a skip.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from omp.adapters.embeddings import HashEmbeddingProvider
from omp.adapters.postgres import create_postgres_uow_factory
from omp.application.models import (
    ForgetMemoryCommand,
    RelateMemoriesCommand,
    SearchFilters,
    SearchMemoryCommand,
    UpdateMemoryCommand,
    WriteMemoryCommand,
)
from omp.application.ports import EmbeddingProfile
from omp.application.services import MemoryApplicationService
from omp.cloud import LocalDevelopmentKMS, TenantEnvelopeEncryptor
from omp.cloud.tenant import TenantContextError, tenant_scope
from omp.config import OMPSettings
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


def _async_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise ValueError("OMP_TEST_DATABASE_URL must be a PostgreSQL URL")


def _run_alembic(command: str, revision: str, url: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["OMP_DATABASE_URL"] = url
    return subprocess.run(
        [sys.executable, "-m", "alembic", command, revision],
        cwd=os.getcwd(),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    raw_url = os.environ.get("OMP_TEST_DATABASE_URL")
    container: Any | None = None
    if raw_url is None:
        try:
            from testcontainers.community.postgres import PostgresContainer

            container = PostgresContainer("pgvector/pgvector:pg16")
            container.start()
            raw_url = container.get_connection_url()
        except Exception as exc:
            if container is not None:
                container.stop()
            message = (
                "PostgreSQL/pgvector unavailable. Set OMP_TEST_DATABASE_URL to a disposable "
                "PostgreSQL 16 + pgvector database or start Docker. "
                f"Original error: {exc}"
            )
            if os.environ.get("OMP_REQUIRE_POSTGRES_TESTS") == "1":
                pytest.fail(message)
            pytest.skip(message)

    assert raw_url is not None
    url = _async_url(raw_url)
    down = _run_alembic("downgrade", "base", url)
    if down.returncode != 0:
        message = f"migration downgrade base failed:\n{down.stdout}\n{down.stderr}"
        if os.environ.get("OMP_REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail(message)
        pytest.skip(message)
    up = _run_alembic("upgrade", "head", url)
    if up.returncode != 0:
        message = f"migration zero -> head failed:\n{up.stdout}\n{up.stderr}"
        if container is not None:
            container.stop()
        pytest.fail(message)

    try:
        yield url
    finally:
        down = _run_alembic("downgrade", "base", url)
        if down.returncode != 0:
            # Teardown cannot change an already reported test result, but the
            # command output remains visible in the test report.
            print(f"migration teardown failed:\n{down.stdout}\n{down.stderr}")
        if container is not None:
            container.stop()


@dataclass
class Runtime:
    app: MemoryApplicationService
    engine: AsyncEngine
    database_url: str


@pytest.fixture
async def runtime(postgres_url: str) -> Iterator[Runtime]:
    settings = OMPSettings(database_url=postgres_url, migration_head="0004_semantic_source_version")
    factory, engine_object = create_postgres_uow_factory(settings)
    assert isinstance(engine_object, AsyncEngine)
    runtime = Runtime(
        app=MemoryApplicationService(
            uow_factory=factory,
            embedding_provider=HashEmbeddingProvider(),
        ),
        engine=engine_object,
        database_url=postgres_url,
    )
    try:
        async with runtime.engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE TABLE idempotency_operations, memory_relations, "
                    "memory_embeddings, memory_embeddings_semantic, memory_versions, "
                    "memories CASCADE"
                )
            )
        yield runtime
    finally:
        await runtime.engine.dispose()


def write_command(
    owner_id: str,
    content: str = "market density strategy",
    *,
    key: str | None = None,
    space: str | None = "alpha",
) -> WriteMemoryCommand:
    return WriteMemoryCommand(
        owner_id=owner_id,
        content=content,
        memory_type=MemoryType.INSIGHT,
        provenance=provenance(owner_id),
        importance=0.9,
        confidence=0.9,
        space=space,
        idempotency_key=key,
    )


async def scalar(engine: AsyncEngine, query: str, **params: object) -> Any:
    async with engine.connect() as connection:
        return (await connection.execute(text(query), params)).scalar_one()


@pytest.mark.asyncio
async def test_cloud_rls_denies_missing_and_cross_tenant_context(runtime: Runtime) -> None:
    """Exercise FORCE RLS through a role that cannot bypass it."""
    role, password = "omp_cloud_rls_test", "omp_cloud_rls_test"
    async with runtime.engine.begin() as connection:
        await connection.execute(
            text(
                "DO $$ BEGIN "
                "CREATE ROLE omp_cloud_rls_test LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD "
                "'omp_cloud_rls_test'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
            )
        )
        await connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        await connection.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON tenants TO {role}"))
        await connection.execute(
            text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON connections TO {role}")
        )

    cloud_url = make_url(runtime.database_url).set(username=role, password=password)
    cloud_engine = create_async_engine(cloud_url.render_as_string(hide_password=False))
    tenant_a, tenant_b, connection_id = uuid4(), uuid4(), uuid4()
    try:
        async with cloud_engine.begin() as connection:
            await connection.execute(
                text("INSERT INTO tenants (id, name) VALUES (:a, 'tenant a'), (:b, 'tenant b')"),
                {"a": tenant_a, "b": tenant_b},
            )
            await connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_a)},
            )
            await connection.execute(
                text(
                    "INSERT INTO connections (id, tenant_id, client_id, scopes) "
                    "VALUES (:id, :tenant_id, 'client-a', ARRAY['memory:read'])"
                ),
                {"id": connection_id, "tenant_id": tenant_a},
            )

        async with cloud_engine.connect() as connection:
            missing_context = await connection.scalar(text("SELECT count(*) FROM connections"))
            assert missing_context == 0

        async with cloud_engine.begin() as connection:
            await connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_b)},
            )
            assert await connection.scalar(text("SELECT count(*) FROM connections")) == 0
            deleted = await connection.execute(
                text("DELETE FROM connections WHERE id = :id"), {"id": connection_id}
            )
            assert deleted.rowcount == 0

        async with cloud_engine.begin() as connection:
            await connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_a)},
            )
            assert await connection.scalar(text("SELECT count(*) FROM connections")) == 1
    finally:
        await cloud_engine.dispose()
        async with runtime.engine.begin() as connection:
            await connection.execute(text(f"DROP OWNED BY {role}"))
            await connection.execute(text(f"DROP ROLE {role}"))


@pytest.mark.asyncio
async def test_cloud_postgres_uow_fails_closed_without_bound_tenant(runtime: Runtime) -> None:
    settings = OMPSettings(
        database_url=runtime.database_url,
        environment="cloud",
        migration_head="0005_cloud_multitenancy_rls",
    )
    factory, engine = create_postgres_uow_factory(
        settings,
        encryptor=TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)),
    )
    try:
        with pytest.raises(TenantContextError):
            async with factory():
                pass
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cloud_postgres_write_persists_bound_tenant_id(runtime: Runtime) -> None:
    tenant = uuid4()
    owner = f"cloud:{tenant}:{uuid4()}"
    async with runtime.engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO tenants (id, name) VALUES (:id, 'cloud write tenant')"),
            {"id": tenant},
        )
    settings = OMPSettings(
        database_url=runtime.database_url,
        environment="cloud",
        migration_head="0005_cloud_multitenancy_rls",
    )
    factory, engine = create_postgres_uow_factory(
        settings,
        encryptor=TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)),
    )
    app = MemoryApplicationService(uow_factory=factory, embedding_provider=HashEmbeddingProvider())
    try:
        with tenant_scope(tenant):
            written = await app.write(write_command(owner, "cloud tenant persistence"))
        assert written.created is True
        persisted_tenant = await scalar(
            engine, "SELECT tenant_id FROM memories WHERE id = :id", id=written.memory.id
        )
        assert persisted_tenant == tenant
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cloud_postgres_blocks_cross_tenant_forged_owner_operations(runtime: Runtime) -> None:
    role, password = "omp_cloud_repo_test", "omp_cloud_repo_test"
    tenant_a, tenant_b = uuid4(), uuid4()
    owner_a = f"cloud:{tenant_a}:{uuid4()}"
    async with runtime.engine.begin() as connection:
        await connection.execute(
            text(
                "DO $$ BEGIN "
                "CREATE ROLE omp_cloud_repo_test LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD "
                "'omp_cloud_repo_test'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
            )
        )
        await connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        await connection.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON tenants, memories, memory_versions, "
                f"memory_embeddings, memory_embeddings_semantic, idempotency_operations TO {role}"
            )
        )
        await connection.execute(
            text("INSERT INTO tenants (id, name) VALUES (:a, 'tenant a'), (:b, 'tenant b')"),
            {"a": tenant_a, "b": tenant_b},
        )
    cloud_url = make_url(runtime.database_url).set(username=role, password=password)
    factory, engine = create_postgres_uow_factory(
        OMPSettings(
            database_url=cloud_url.render_as_string(hide_password=False), environment="cloud"
        ),
        encryptor=TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)),
    )
    app = MemoryApplicationService(uow_factory=factory, embedding_provider=HashEmbeddingProvider())
    try:
        with tenant_scope(tenant_a):
            written = await app.write(write_command(owner_a, "tenant a private memory"))
        with tenant_scope(tenant_b):
            async with factory() as uow:
                assert await uow.memories.get(owner_id=owner_a, memory_id=written.memory.id) is None
            with pytest.raises(NotFoundError):
                await app.update(
                    UpdateMemoryCommand(
                        owner_id=owner_a,
                        memory_id=written.memory.id,
                        expected_version=1,
                        content="forged update",
                        idempotency_key="forged-update",
                    )
                )
            forged_forget = await app.forget(
                ForgetMemoryCommand(
                    owner_id=owner_a,
                    memory_id=written.memory.id,
                    idempotency_key="forged-forget",
                )
            )
            assert forged_forget.forgotten is False
        with tenant_scope(tenant_a):
            async with factory() as uow:
                assert await uow.memories.get(owner_id=owner_a, memory_id=written.memory.id)
    finally:
        await engine.dispose()
        async with runtime.engine.begin() as connection:
            await connection.execute(text(f"DROP OWNED BY {role}"))
            await connection.execute(text(f"DROP ROLE {role}"))


SEMANTIC_PROFILE = EmbeddingProfile("semantic", "e5-small-v2-s09", 384)
SEMANTIC_VECTOR = (1.0,) + (0.0,) * 383


class StaticSemanticProvider:
    @property
    def profile(self) -> EmbeddingProfile:
        return SEMANTIC_PROFILE

    async def embed(self, text: str, *, query: bool = False) -> tuple[float, ...]:
        return SEMANTIC_VECTOR


def semantic_application(
    runtime: Runtime,
) -> tuple[MemoryApplicationService, Any, AsyncEngine]:
    factory, engine_object = create_postgres_uow_factory(
        OMPSettings(
            database_url=runtime.database_url,
            migration_head="0004_semantic_source_version",
        )
    )
    assert isinstance(engine_object, AsyncEngine)
    return (
        MemoryApplicationService(
            uow_factory=factory,
            embedding_provider=StaticSemanticProvider(),
        ),
        factory,
        engine_object,
    )


@pytest.mark.asyncio
async def test_migration_head_and_pgvector_are_real(runtime: Runtime) -> None:
    assert (
        await scalar(runtime.engine, "SELECT extname FROM pg_extension WHERE extname = 'vector'")
        == "vector"
    )
    assert (
        await scalar(
            runtime.engine,
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN "
            "('memories', 'memory_versions', 'memory_embeddings', 'memory_embeddings_semantic', "
            "'memory_relations', "
            "'idempotency_operations')",
        )
        == 6
    )
    assert (
        await scalar(
            runtime.engine,
            "SELECT count(*) FROM pg_indexes "
            "WHERE indexname = 'ix_memory_embeddings_vector_cosine'",
        )
        == 1
    )


@pytest.mark.asyncio
async def test_real_write_replay_conflict_and_owner_isolation(runtime: Runtime) -> None:
    first, replay = await asyncio.gather(
        runtime.app.write(write_command("owner-a", key="write-race")),
        runtime.app.write(write_command("owner-a", key="write-race")),
    )
    assert len({first.memory.id, replay.memory.id}) == 1
    assert sorted((first.created, replay.created)) == [False, True]
    other_owner = await runtime.app.write(write_command("owner-b", key="write-race"))
    assert other_owner.created is True
    with pytest.raises(IdempotencyConflictError):
        await runtime.app.write(write_command("owner-a", "different payload", key="write-race"))
    result = await runtime.app.search(
        SearchMemoryCommand(owner_id="owner-a", query="market density strategy")
    )
    assert {item.memory.owner_id for item in result.items} == {"owner-a"}
    assert {item.memory.id for item in result.items} == {first.memory.id}


@pytest.mark.asyncio
async def test_real_update_replay_stale_and_distinct_concurrency(runtime: Runtime) -> None:
    created = await runtime.app.write(write_command("owner-a"))
    update = UpdateMemoryCommand(
        owner_id="owner-a",
        memory_id=created.memory.id,
        expected_version=1,
        content="first persisted update",
        idempotency_key="update-race",
    )
    first, replay = await asyncio.gather(runtime.app.update(update), runtime.app.update(update))
    assert first.version == replay.version == 2
    assert first.content == replay.content
    changed = await runtime.app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=created.memory.id,
            expected_version=2,
            content="later update",
        )
    )
    assert changed.version == 3
    historical = await runtime.app.update(update)
    assert historical.version == 2
    assert historical.content == "first persisted update"

    left = UpdateMemoryCommand(
        owner_id="owner-a", memory_id=created.memory.id, expected_version=3, content="left"
    )
    right = UpdateMemoryCommand(
        owner_id="owner-a", memory_id=created.memory.id, expected_version=3, content="right"
    )
    outcomes = await asyncio.gather(
        runtime.app.update(left), runtime.app.update(right), return_exceptions=True
    )
    assert sum(isinstance(item, VersionConflictError) for item in outcomes) == 1
    assert sum(not isinstance(item, Exception) for item in outcomes) == 1


@pytest.mark.asyncio
async def test_search_filters_threshold_active_and_profile(runtime: Runtime) -> None:
    active = await runtime.app.write(write_command("owner-a", "same query", space="alpha"))
    archived = await runtime.app.write(write_command("owner-a", "same query", space="beta"))
    await runtime.app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=archived.memory.id,
            expected_version=1,
            state=MemoryState.ARCHIVED,
        )
    )
    default = await runtime.app.search(SearchMemoryCommand(owner_id="owner-a", query="same query"))
    assert [item.memory.id for item in default.items] == [active.memory.id]
    filtered = await runtime.app.search(
        SearchMemoryCommand(
            owner_id="owner-a",
            query="same query",
            filters=SearchFilters(states=frozenset({MemoryState.ARCHIVED}), space="beta"),
        )
    )
    assert [item.memory.id for item in filtered.items] == [archived.memory.id]
    assert (
        await runtime.app.search(
            SearchMemoryCommand(
                owner_id="owner-a", query="unrelated quantum cooking", threshold=0.99
            )
        )
    ).items == ()

    other_factory, other_engine_object = create_postgres_uow_factory(
        OMPSettings(
            database_url=runtime.database_url,
            migration_head="0004_semantic_source_version",
        )
    )
    assert isinstance(other_engine_object, AsyncEngine)
    try:
        v2_app = MemoryApplicationService(
            uow_factory=other_factory,
            embedding_provider=HashEmbeddingProvider(version="v2"),
        )
        await v2_app.write(write_command("owner-a", "v2 only"))
        v1 = await runtime.app.search(SearchMemoryCommand(owner_id="owner-a", query="v2 only"))
        assert all(item.profile_version == "v1" for item in v1.items)
    finally:
        await other_engine_object.dispose()


@pytest.mark.asyncio
async def test_semantic_profile_coexists_cutover_and_forget_cascades(runtime: Runtime) -> None:
    created = await runtime.app.write(write_command("owner-a", "semantic parallel profile"))
    profile = EmbeddingProfile("semantic", "e5-small-v2-s09", 384)
    vector = (1.0,) + (0.0,) * 383
    factory, engine_object = create_postgres_uow_factory(
        OMPSettings(
            database_url=runtime.database_url,
            migration_head="0004_semantic_source_version",
        )
    )

    class StaticSemanticProvider:
        @property
        def profile(self) -> EmbeddingProfile:
            return profile

        async def embed(self, text: str, *, query: bool = False) -> tuple[float, ...]:
            return vector

    try:
        async with factory() as uow:
            assert await uow.memories.upsert_embedding_profile(
                memory_id=created.memory.id,
                expected_version=created.memory.version,
                profile=profile,
                embedding=vector,
            )
        semantic_app = MemoryApplicationService(
            uow_factory=factory, embedding_provider=StaticSemanticProvider()
        )
        before_cutover = await semantic_app.search(
            SearchMemoryCommand(owner_id="owner-a", query="semantic query")
        )
        assert [item.memory.id for item in before_cutover.items] == [created.memory.id]
        async with factory() as uow:
            assert (
                await uow.memories.cutover_embedding_profile(owner_id="owner-a", profile=profile)
                == 1
            )
        after_cutover = await semantic_app.search(
            SearchMemoryCommand(owner_id="owner-a", query="semantic query")
        )
        assert [item.memory.id for item in after_cutover.items] == [created.memory.id]
        await semantic_app.forget(
            ForgetMemoryCommand(owner_id="owner-a", memory_id=created.memory.id)
        )
        assert (
            await scalar(
                runtime.engine,
                "SELECT count(*) FROM memory_embeddings_semantic WHERE memory_id = :id",
                id=created.memory.id,
            )
            == 0
        )
        assert (
            await scalar(
                runtime.engine,
                "SELECT count(*) FROM memory_embeddings WHERE memory_id = :id",
                id=created.memory.id,
            )
            == 0
        )
    finally:
        await engine_object.dispose()


@pytest.mark.asyncio
async def test_cloud_postgres_envelopes_content_and_provenance(postgres_url: str) -> None:
    tenant = uuid4()
    settings = OMPSettings(
        database_url=postgres_url,
        environment="cloud",
        migration_head="0006_cloud_envelope_storage",
    )
    factory, engine_object = create_postgres_uow_factory(
        settings,
        encryptor=TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)),
    )
    assert isinstance(engine_object, AsyncEngine)
    app = MemoryApplicationService(uow_factory=factory, embedding_provider=HashEmbeddingProvider())
    try:
        async with engine_object.begin() as connection:
            await connection.execute(
                text("INSERT INTO tenants (id, name) VALUES (:id, 'encrypted')"), {"id": tenant}
            )
        with tenant_scope(tenant):
            created = await app.write(write_command(f"cloud:{tenant}:subject", "postgres canary"))
            async with factory() as uow:
                found = await uow.memories.get(
                    owner_id=f"cloud:{tenant}:subject", memory_id=created.memory.id
                )
        assert found is not None and found.id == created.memory.id
        with tenant_scope(tenant):
            async with factory() as uow:
                assert await uow.memories.rewrap_envelopes(key_version=2) == 1
                reread = await uow.memories.get(
                    owner_id=f"cloud:{tenant}:subject", memory_id=created.memory.id
                )
        assert reread is not None and reread.content == "postgres canary"
        async with engine_object.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT content, provenance, content_ciphertext, provenance_ciphertext "
                        "FROM memories WHERE id = :id"
                    ),
                    {"id": created.memory.id},
                )
            ).one()._mapping
        assert row["content"] is None and row["provenance"] is None
        assert "postgres canary" not in row["content_ciphertext"]
        assert "postgres canary" not in row["provenance_ciphertext"]
        assert json.loads(row["content_ciphertext"])["k"] == 2
        history_key_version = await scalar(
            engine_object,
            "SELECT (content_ciphertext::jsonb ->> 'k')::int FROM memory_versions "
            "WHERE memory_id = :id AND version = 1",
            id=created.memory.id,
        )
        assert history_key_version == 2
        with tenant_scope(tenant):
            forgotten = await app.forget(
                ForgetMemoryCommand(
                    owner_id=f"cloud:{tenant}:subject",
                    memory_id=created.memory.id,
                    idempotency_key="encrypted-forget",
                )
            )
        assert forgotten.forgotten is True
        async with engine_object.connect() as connection:
            tombstone = (
                await connection.execute(
                    text(
                        "SELECT tenant_id, memory_id, subject_id, reason "
                        "FROM deletion_tombstones WHERE memory_id = :id"
                    ),
                    {"id": created.memory.id},
                )
            ).one()._mapping
        assert tombstone["tenant_id"] == tenant
        assert tombstone["memory_id"] == created.memory.id
        assert tombstone["subject_id"] is None
        assert tombstone["reason"] == "memory.forget"
    finally:
        await engine_object.dispose()


@pytest.mark.asyncio
async def test_semantic_source_version_is_written_updated_imported_and_stale_safe(
    runtime: Runtime,
) -> None:
    semantic_app, factory, engine_object = semantic_application(runtime)
    try:
        created = await semantic_app.write(write_command("owner-semantic", "semantic source"))
        assert created.memory.version == 1
        assert (
            await scalar(
                runtime.engine,
                "SELECT source_version FROM memory_embeddings_semantic WHERE memory_id = :id",
                id=created.memory.id,
            )
            == 1
        )

        updated = await semantic_app.update(
            UpdateMemoryCommand(
                owner_id="owner-semantic",
                memory_id=created.memory.id,
                expected_version=1,
                content="semantic source v2",
            )
        )
        assert updated.version == 2
        assert (
            await scalar(
                runtime.engine,
                "SELECT source_version FROM memory_embeddings_semantic WHERE memory_id = :id",
                id=created.memory.id,
            )
            == 2
        )

        exported = await semantic_app.export_memories(
            owner_id="owner-semantic",
            include_embeddings=True,
        )
        assert exported[0].embedding is not None
        async with runtime.engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE TABLE idempotency_operations, memory_relations, "
                    "memory_embeddings, memory_embeddings_semantic, memory_versions, "
                    "memories CASCADE"
                )
            )
        imported = await semantic_app.import_memories(owner_id="owner-semantic", records=exported)
        assert imported.imported == 1
        assert (
            await scalar(
                runtime.engine,
                "SELECT source_version FROM memory_embeddings_semantic WHERE memory_id = :id",
                id=created.memory.id,
            )
            == 2
        )

        hash_memory = await runtime.app.write(write_command("owner-stale", "hash source"))
        async with factory() as uow:
            assert await uow.memories.upsert_embedding_profile(
                memory_id=hash_memory.memory.id,
                expected_version=1,
                profile=SEMANTIC_PROFILE,
                embedding=SEMANTIC_VECTOR,
            )
        await runtime.app.update(
            UpdateMemoryCommand(
                owner_id="owner-stale",
                memory_id=hash_memory.memory.id,
                expected_version=1,
                content="hash source v2",
            )
        )
        async with factory() as uow:
            assert not await uow.memories.upsert_embedding_profile(
                memory_id=hash_memory.memory.id,
                expected_version=1,
                profile=SEMANTIC_PROFILE,
                embedding=SEMANTIC_VECTOR,
            )
        stale_search = await semantic_app.search(
            SearchMemoryCommand(owner_id="owner-stale", query="hash source")
        )
        assert stale_search.items == ()
        assert await scalar(runtime.engine, "SELECT count(*) FROM memory_embeddings") == 1
        assert (
            await scalar(
                runtime.engine,
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'memory_embeddings' AND column_name = 'source_version'",
            )
            == 0
        )
        assert (
            await scalar(
                runtime.engine,
                "SELECT count(*) FROM memory_embeddings_semantic WHERE source_version < 1",
            )
            == 0
        )
    finally:
        await engine_object.dispose()


@pytest.mark.asyncio
async def test_history_relations_forget_cascade_and_repeated_forget(runtime: Runtime) -> None:
    source = await runtime.app.write(write_command("owner-a", "source"))
    target = await runtime.app.write(write_command("owner-a", "target"))
    await runtime.app.relate(
        RelateMemoriesCommand("owner-a", source.memory.id, target.memory.id, "related_to")
    )
    await runtime.app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=source.memory.id,
            expected_version=1,
            content="source v2",
            idempotency_key="source-update",
        )
    )
    async with runtime.engine.connect() as connection:
        versions = (
            await connection.execute(
                text("SELECT count(*) FROM memory_versions WHERE memory_id = :id"),
                {"id": source.memory.id},
            )
        ).scalar_one()
        relations = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM memory_relations WHERE source_id = :id OR target_id = :id"
                ),
                {"id": source.memory.id},
            )
        ).scalar_one()
    assert versions == 2
    assert relations == 1
    forgotten = await runtime.app.forget(
        ForgetMemoryCommand("owner-a", source.memory.id, idempotency_key="forget-source")
    )
    repeated = await runtime.app.forget(
        ForgetMemoryCommand("owner-a", source.memory.id, idempotency_key="forget-source")
    )
    assert forgotten.forgotten is True
    assert repeated.forgotten is False
    async with runtime.engine.connect() as connection:
        counts = await connection.execute(
            text(
                "SELECT "
                "(SELECT count(*) FROM memories WHERE id = :id) AS memories, "
                "(SELECT count(*) FROM memory_versions WHERE memory_id = :id) AS versions, "
                "(SELECT count(*) FROM memory_embeddings WHERE memory_id = :id) AS embeddings, "
                "(SELECT count(*) FROM memory_relations "
                "WHERE source_id = :id OR target_id = :id) AS relations"
            ),
            {"id": source.memory.id},
        )
        row = counts.one()._mapping
        ledger = await connection.execute(
            text(
                "SELECT status, result_status FROM idempotency_operations "
                "WHERE owner_id = 'owner-a' AND operation_type = 'forget' "
                "AND idempotency_key = 'forget-source'"
            )
        )
        ledger_row = ledger.one()._mapping
    assert dict(row) == {"memories": 0, "versions": 0, "embeddings": 0, "relations": 0}
    assert dict(ledger_row) == {"status": "completed", "result_status": "forgotten"}


@pytest.mark.asyncio
async def test_cross_owner_read_update_relation_and_forget_are_blocked(runtime: Runtime) -> None:
    created = await runtime.app.write(write_command("owner-a"))
    assert (
        await runtime.app.search(
            SearchMemoryCommand(owner_id="owner-b", query="market density strategy")
        )
    ).items == ()
    with pytest.raises(NotFoundError):
        await runtime.app.update(
            UpdateMemoryCommand("owner-b", created.memory.id, expected_version=1, content="attack")
        )
    assert not (
        await runtime.app.forget(ForgetMemoryCommand("owner-b", created.memory.id))
    ).forgotten
    with pytest.raises(NotFoundError):
        await runtime.app.relate(
            RelateMemoriesCommand("owner-b", created.memory.id, UUID(int=0), "related_to")
        )


@pytest.mark.asyncio
async def test_failed_update_rolls_back_ledger_and_memory(runtime: Runtime) -> None:
    class ToggleProvider(HashEmbeddingProvider):
        bad = False

        async def embed(self, text: str, *, query: bool = False) -> tuple[float, ...]:
            if self.bad:
                return (0.0, 1.0, 0.0)
            return tuple(await super().embed(text))

    provider = ToggleProvider()
    factory, engine_object = create_postgres_uow_factory(
        OMPSettings(
            database_url=runtime.database_url,
            migration_head="0004_semantic_source_version",
        )
    )
    assert isinstance(engine_object, AsyncEngine)
    app = MemoryApplicationService(uow_factory=factory, embedding_provider=provider)
    try:
        created = await app.write(write_command("owner-a"))
        provider.bad = True
        command = UpdateMemoryCommand(
            "owner-a",
            created.memory.id,
            expected_version=1,
            content="retry",
            idempotency_key="retry",
        )
        with pytest.raises(ValidationError):
            await app.update(command)
        provider.bad = False
        retried = await app.update(command)
        assert retried.version == 2
        async with engine_object.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT status, result_version FROM idempotency_operations "
                            "WHERE owner_id = 'owner-a' AND operation_type = 'update' "
                            "AND idempotency_key = 'retry'"
                        )
                    )
                )
                .one()
                ._mapping
            )
        assert dict(row) == {"status": "completed", "result_version": 2}
    finally:
        await engine_object.dispose()


@pytest.mark.asyncio
async def test_vector_explain_and_owner_scoped_relation_constraint(runtime: Runtime) -> None:
    created_a = await runtime.app.write(write_command("owner-a", "explain vector"))
    created_b = await runtime.app.write(write_command("owner-b", "other owner"))
    vector = "[" + ",".join("0" for _ in range(64)) + "]"
    async with runtime.engine.connect() as connection:
        plan = (
            (
                await connection.execute(
                    text(
                        "EXPLAIN (FORMAT TEXT) SELECT memory_id FROM memory_embeddings "
                        "ORDER BY vector <=> CAST(:vector AS vector) LIMIT 1"
                    ),
                    {"vector": vector},
                )
            )
            .scalars()
            .all()
        )
        assert plan
        with pytest.raises(IntegrityError):
            await connection.execute(
                text(
                    "INSERT INTO memory_relations "
                    "(owner_id, source_id, target_id, relation_type, created_at) "
                    "VALUES ('owner-b', :source, :target, 'related_to', now())"
                ),
                {"source": created_a.memory.id, "target": created_b.memory.id},
            )


@pytest.mark.asyncio
async def test_postgres_export_import_round_trip_without_embeddings(runtime: Runtime) -> None:
    source = await runtime.app.write(write_command("owner-a", "export source"))
    target = await runtime.app.write(write_command("owner-a", "export target"))
    await runtime.app.relate(
        RelateMemoriesCommand("owner-a", source.memory.id, target.memory.id, "related_to")
    )
    await runtime.app.update(
        UpdateMemoryCommand(
            owner_id="owner-a",
            memory_id=source.memory.id,
            expected_version=1,
            content="export source v2",
        )
    )
    records = await runtime.app.export_memories(owner_id="owner-a")
    assert len(records) == 2
    assert all(record.embedding is None for record in records)
    assert {len(record.history) for record in records} == {1, 2}

    async with runtime.engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE idempotency_operations, memory_relations, "
                "memory_embeddings, memory_versions, memories CASCADE"
            )
        )
    imported = await runtime.app.import_memories(owner_id="owner-a", records=records)
    replayed = await runtime.app.import_memories(owner_id="owner-a", records=records)
    assert imported.imported == 2
    assert imported.replayed == 0
    assert replayed.imported == 0
    assert replayed.replayed == 2
    async with runtime.engine.connect() as connection:
        counts = await connection.execute(
            text(
                "SELECT "
                "(SELECT count(*) FROM memories) AS memories, "
                "(SELECT count(*) FROM memory_versions) AS versions, "
                "(SELECT count(*) FROM memory_embeddings) AS embeddings, "
                "(SELECT count(*) FROM memory_relations) AS relations"
            )
        )
        row = counts.one()._mapping
    assert dict(row) == {"memories": 2, "versions": 3, "embeddings": 2, "relations": 1}


@pytest.mark.asyncio
async def test_postgres_import_validates_before_mutation_and_conflicts(runtime: Runtime) -> None:
    created = await runtime.app.write(write_command("owner-a", "import canonical"))
    records = await runtime.app.export_memories(owner_id="owner-a")
    invalid = replace(records[0], memory=replace(records[0].memory, owner_id="owner-b"))
    async with runtime.engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE idempotency_operations, memory_relations, "
                "memory_embeddings, memory_versions, memories CASCADE"
            )
        )
    with pytest.raises(ValidationError):
        await runtime.app.import_memories(owner_id="owner-a", records=(records[0], invalid))
    assert await scalar(runtime.engine, "SELECT count(*) FROM memories") == 0

    await runtime.app.import_memories(owner_id="owner-a", records=records)
    divergent = replace(records[0], memory=replace(records[0].memory, content="different"))
    with pytest.raises(ImportConflictError):
        await runtime.app.import_memories(owner_id="owner-a", records=(divergent,))
    assert (
        await scalar(
            runtime.engine, "SELECT content FROM memories WHERE id = :id", id=created.memory.id
        )
        == "import canonical"
    )


@pytest.mark.asyncio
async def test_postgres_import_uses_supplied_embeddings_and_profile_policy(
    runtime: Runtime,
) -> None:
    await runtime.app.write(write_command("owner-a", "profile export"))
    records = await runtime.app.export_memories(owner_id="owner-a", include_embeddings=True)
    assert records[0].embedding is not None
    async with runtime.engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE idempotency_operations, memory_relations, "
                "memory_embeddings, memory_versions, memories CASCADE"
            )
        )

    factory, engine_object = create_postgres_uow_factory(
        OMPSettings(
            database_url=runtime.database_url,
            migration_head="0004_semantic_source_version",
        )
    )
    assert isinstance(engine_object, AsyncEngine)
    try:
        incompatible = MemoryApplicationService(
            uow_factory=factory,
            embedding_provider=HashEmbeddingProvider(version="v2"),
        )
        with pytest.raises(EmbeddingProfileMismatchError):
            await incompatible.import_memories(
                owner_id="owner-a",
                records=tuple(replace(record, embedding=None) for record in records),
            )
        imported = await incompatible.import_memories(owner_id="owner-a", records=records)
        assert imported.imported == 1
        assert await scalar(runtime.engine, "SELECT count(*) FROM memory_embeddings") == 1
    finally:
        await engine_object.dispose()
