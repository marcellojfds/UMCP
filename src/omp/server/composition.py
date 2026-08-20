"""Explicit Alpha composition for Postgres and opt-in demo backends."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import text

from omp.adapters.embeddings.hash_provider import HashEmbeddingProvider
from omp.adapters.mcp.adapter import MCPAdapter
from omp.adapters.mcp.application_gateway import MemoryApplicationGateway
from omp.adapters.mcp.local import PersistentLocalMemoryService
from omp.adapters.postgres.repository import create_postgres_uow_factory
from omp.application.services import MemoryApplicationService
from omp.config import OMPSettings, get_settings
from omp.domain import utc_now


@dataclass(slots=True)
class ServerRuntime:
    settings: OMPSettings
    adapter: MCPAdapter
    backend: str
    engine: Any | None = None
    service: Any | None = None
    _closed: bool = False

    async def startup(self) -> None:
        if self.backend == "postgres" and not await self.readiness():
            raise RuntimeError("postgres readiness check failed")

    async def readiness(self) -> bool:
        if self.backend == "demo":
            return True
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
    settings: OMPSettings | None = None, *, demo_backend: bool = False
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

    uow_factory, engine = create_postgres_uow_factory(selected)
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
    )


def create_demo_runtime(settings: OMPSettings | None = None) -> ServerRuntime:
    return create_runtime(settings, demo_backend=True)
