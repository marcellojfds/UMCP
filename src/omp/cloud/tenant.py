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
    if not isinstance(tenant_id, UUID):
        raise TenantContextError("tenant context must be a UUID")
    token: Token[UUID | None] = _tenant_context.set(tenant_id)
    try:
        yield
    finally:
        _tenant_context.reset(token)


@contextmanager
def verified_principal_scope(principal: object) -> Iterator[None]:
    """Bind a tenant only from the immutable, already-verified H04 principal.

    The local adapter keeps the UUID-only ``tenant_scope`` for compatibility
    with existing service tests. Hosted composition should use this seam so a
    request cannot manufacture tenancy from a transport field.
    """
    from .security import Principal

    if not isinstance(principal, Principal):
        raise TenantContextError("verified principal is required")
    try:
        principal.requires(next(iter(principal.scopes)))
    except (PermissionError, StopIteration) as exc:
        raise TenantContextError("verified principal is expired or has no scope") from exc
    with tenant_scope(principal.tenant_id):
        yield


def current_tenant() -> UUID:
    tenant_id = _tenant_context.get()
    if tenant_id is None:
        raise TenantContextError("tenant context is required")
    return tenant_id


def current_tenant_or_none() -> UUID | None:
    """Read the request binding without turning Community transactions into Cloud."""
    return _tenant_context.get()


async def set_tenant_context(session: AsyncSession, tenant_id: UUID | None) -> None:
    """Set PostgreSQL LOCAL context; it dies with the transaction.

    The database policy reads this exact setting. Passing ``None`` is rejected
    instead of running an unscoped query.
    """
    if tenant_id is None:
        raise TenantContextError("tenant context is required")
    if tenant_id != current_tenant():
        raise TenantContextError("tenant context does not match the verified principal")
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
