"""Explicit Alpha composition for Postgres and opt-in demo backends."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import text

from omp.adapters.embeddings import HashEmbeddingProvider, LocalTransformerEmbeddingProvider
from omp.adapters.mcp.adapter import MCPAdapter, TenantWindowRateLimiter
from omp.adapters.mcp.application_gateway import MemoryApplicationGateway
from omp.adapters.mcp.local import PersistentLocalMemoryService
from omp.adapters.postgres.repository import create_postgres_uow_factory
from omp.application.services import MemoryApplicationService
from omp.cloud.encrypted_memory import EncryptedCloudMemoryService
from omp.cloud.security import (
    GoogleCloudKMS,
    HostedKMSUnavailable,
    LocalDevelopmentKMS,
    TenantEnvelopeEncryptor,
)
from omp.config import OMPSettings, get_settings
from omp.domain import utc_now


@dataclass(slots=True)
class ServerRuntime:
    settings: OMPSettings
    adapter: MCPAdapter
    backend: str
    engine: Any | None = None
    service: Any | None = None
    embedding_provider: Any | None = None
    _closed: bool = False

    async def startup(self) -> None:
        if self.embedding_provider is not None and hasattr(self.embedding_provider, "startup"):
            await self.embedding_provider.startup()
        if self.backend == "postgres" and not await self.readiness():
            raise RuntimeError("postgres readiness check failed")

    async def readiness(self) -> bool:
        if self.backend == "demo":
            return True
        if self.embedding_provider is not None and hasattr(self.embedding_provider, "ready"):
            if not bool(self.embedding_provider.ready):
                return False
        if self.engine is None:
            return False
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                extension = await connection.scalar(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                )
                revision = await connection.scalar(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                return bool(extension == 1 and revision == self.settings.migration_head)
        except Exception:
            return False

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.engine is not None:
            await self.engine.dispose()


def create_runtime(
    settings: OMPSettings | None = None,
    *,
    demo_backend: bool = False,
    encryptor: TenantEnvelopeEncryptor | None = None,
) -> ServerRuntime:
    """Create an unconnected runtime; connections happen in ``startup``."""

    selected = settings or get_settings()
    backend = "demo" if demo_backend or selected.backend == "demo" else "postgres"
    if backend == "demo":
        service: Any = PersistentLocalMemoryService(selected.demo_data_file)
        return ServerRuntime(
            settings=selected,
            adapter=MCPAdapter(service, local_mode=True, transport="stdio"),
            backend="demo",
            service=service,
        )

    uow_factory, engine = create_postgres_uow_factory(selected, encryptor=encryptor)
    if selected.embedding_provider == "e5":
        if selected.embedding_dimension != 384:
            raise ValueError("OMP_EMBEDDING_DIMENSION must be 384 when E5 is selected")
        embedding_provider: Any = LocalTransformerEmbeddingProvider(
            model_root=selected.semantic_model_root,
            model_id=selected.semantic_model_id,
            model_revision=selected.semantic_model_revision,
            profile_id=selected.embedding_profile_id,
            profile_version=selected.embedding_profile_version,
            dimension=selected.embedding_dimension,
            query_prefix=selected.semantic_query_prefix,
            passage_prefix=selected.semantic_passage_prefix,
            max_length=selected.semantic_max_length,
        )
    else:
        embedding_provider = HashEmbeddingProvider(
            dimension=selected.embedding_dimension,
            profile_id=selected.embedding_profile_id,
            version=selected.embedding_profile_version,
        )
    service = MemoryApplicationService(
        uow_factory=cast(Callable[[], Any], uow_factory),
        embedding_provider=embedding_provider,
        clock=utc_now,
    )
    gateway = MemoryApplicationGateway(service)
    return ServerRuntime(
        settings=selected,
        adapter=MCPAdapter(gateway, local_mode=True, transport="stdio"),
        backend="postgres",
        engine=engine,
        service=service,
        embedding_provider=embedding_provider,
    )


def create_demo_runtime(settings: OMPSettings | None = None) -> ServerRuntime:
    return create_runtime(settings, demo_backend=True)


def create_cloud_demo_runtime(
    settings: OMPSettings | None = None, *, kms_master_key: bytes
) -> ServerRuntime:
    """Create the local encrypted Cloud adapter used by HTTP/Admin contracts."""
    selected = settings or get_settings()
    service = EncryptedCloudMemoryService(
        TenantEnvelopeEncryptor(LocalDevelopmentKMS(kms_master_key))
    )
    return ServerRuntime(
        settings=selected,
        adapter=MCPAdapter(
            service,
            local_mode=True,
            transport="http",
            rate_limiter=TenantWindowRateLimiter(maximum=300, window_seconds=60),
        ),
        backend="cloud-demo",
        service=service,
    )


def create_cloud_postgres_runtime(
    settings: OMPSettings | None = None, *, kms_master_key: bytes
) -> ServerRuntime:
    """Build the local Cloud PostgreSQL composition with envelope encryption.

    The caller must supply development key material explicitly. Production
    composition should provide a configured KMS implementation instead.
    """
    selected = settings or get_settings()
    if selected.environment != "cloud":
        selected = selected.model_copy(update={"environment": "cloud"})
    return create_runtime(
        selected,
        encryptor=TenantEnvelopeEncryptor(LocalDevelopmentKMS(kms_master_key)),
    )


def create_fail_closed_cloud_runtime(settings: OMPSettings | None = None) -> ServerRuntime:
    """Build the container's hosted runtime without a local-development KMS.

    A real hosted KMS adapter is deliberately outside this repository's local
    scope.  The unavailable implementation ensures a misconfigured image
    cannot silently fall back to plaintext or the synthetic M1 composition.
    """
    selected = settings or get_settings()
    if selected.environment != "cloud":
        selected = selected.model_copy(update={"environment": "cloud"})
    kms = (
        GoogleCloudKMS(selected.kms_key_resource)
        if selected.kms_key_resource
        else HostedKMSUnavailable()
    )
    return create_runtime(selected, encryptor=TenantEnvelopeEncryptor(kms))
