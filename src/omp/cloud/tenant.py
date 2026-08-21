"""Transaction-scoped Cloud tenant context for PostgreSQL adapters."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TenantContextError(PermissionError):
    """Raised before any Cloud query when a verified tenant is absent."""


_tenant_context: ContextVar[UUID | None] = ContextVar("omp_cloud_tenant", default=None)


@contextmanager
def tenant_scope(tenant_id: UUID) -> Iterator[None]:
    """Bind a verified tenant to the current async request context only."""
    token: Token[UUID | None] = _tenant_context.set(tenant_id)
    try:
        yield
    finally:
        _tenant_context.reset(token)


def current_tenant() -> UUID:
    tenant_id = _tenant_context.get()
    if tenant_id is None:
        raise TenantContextError("tenant context is required")
    return tenant_id


async def set_tenant_context(session: AsyncSession, tenant_id: UUID | None) -> None:
    """Set PostgreSQL LOCAL context; it dies with the transaction.

    The database policy reads this exact setting. Passing ``None`` is rejected
    instead of running an unscoped query.
    """
    if tenant_id is None:
        raise TenantContextError("tenant context is required")
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": str(tenant_id)}
    )


async def require_tenant_context(session: AsyncSession) -> UUID:
    value = await session.scalar(text("SELECT current_setting('app.tenant_id', true)"))
    if not value:
        raise TenantContextError("tenant context is required")
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise TenantContextError("tenant context is invalid") from exc
