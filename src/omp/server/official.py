"""Official MCP SDK server composition for the supported stdio transport."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, cast

import anyio
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl, Field

from omp.adapters.mcp.schemas import (
    DEFAULT_TIMEOUT_MS,
    MAX_CONTENT_LENGTH,
    MAX_QUERY_LENGTH,
    MAX_TIMEOUT_MS,
    MemoryPatch,
    MemoryState,
    MemoryType,
    Provenance,
)
from omp.cloud import OIDCTokenVerifier, Scope, principal_from_access_token
from omp.cloud.tenant import tenant_scope

from .composition import ServerRuntime


def create_official_server(runtime: ServerRuntime) -> FastMCP:
    server = FastMCP(
        name="open-memory-protocol",
        instructions=(
            "Use the four memory tools conservatively; an empty search is a valid abstention."
        ),
    )

    @server.tool(name="memory.write", structured_output=False)
    async def memory_write(
        content: Annotated[str, Field(min_length=1, max_length=MAX_CONTENT_LENGTH)],
        type: MemoryType,
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        provenance: Provenance,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        space: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        importance: Annotated[float, Field(ge=0, le=1)] = 0.5,
        confidence: Annotated[float, Field(ge=0, le=1)] = 0.5,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.write", locals())

    @server.tool(name="memory.search", structured_output=False)
    async def memory_search(
        query: Annotated[str, Field(min_length=1, max_length=MAX_QUERY_LENGTH)],
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        space: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        type: MemoryType | None = None,
        state: MemoryState | None = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
        min_relevance: Annotated[float, Field(ge=0, le=1)] = 0.78,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.search", locals())

    @server.tool(name="memory.update", structured_output=False)
    async def memory_update(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        expected_version: Annotated[int, Field(ge=1)],
        patch: MemoryPatch,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        provenance: Provenance | None = None,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.update", locals())

    @server.tool(name="memory.forget", structured_output=False)
    async def memory_forget(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        reason: Annotated[str | None, Field(max_length=256)] = None,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.forget", locals())

    for tool in server._tool_manager._tools.values():  # official SDK tool registry
        tool.parameters["additionalProperties"] = False

    return server


def create_cloud_server(
    runtime: ServerRuntime, verifier: OIDCTokenVerifier, *, allowed_hosts: list[str] | None = None
) -> FastMCP:
    """Create the authenticated Streamable HTTP MCP composition.

    Unlike the Community stdio server, no hosted tool has an ``owner_id``
    argument. The verified bearer claim is converted to the internal temporary
    compatibility owner only at the adapter boundary.
    """
    server = FastMCP(
        name="umcp-cloud",
        instructions="Use memory tools only within the scopes granted to this integration.",
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=cast(AnyHttpUrl, "https://local.umcp.invalid"),
            resource_server_url=cast(AnyHttpUrl, "https://local.umcp.invalid/mcp"),
            required_scopes=[],
        ),
        streamable_http_path="/mcp",
        stateless_http=True,
        max_request_body_size=64 * 1024,
        transport_security=TransportSecuritySettings(
            allowed_hosts=allowed_hosts or ["local.umcp.invalid"]
        ),
    )

    @server.tool(
        name="memory.write",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    )
    async def memory_write_cloud(
        content: Annotated[str, Field(min_length=1, max_length=MAX_CONTENT_LENGTH)],
        type: MemoryType,
        provenance: Provenance,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        space: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        importance: Annotated[float, Field(ge=0, le=1)] = 0.5,
        confidence: Annotated[float, Field(ge=0, le=1)] = 0.5,
    ) -> str:
        return await _call_cloud(runtime, "memory.write", locals(), Scope.MEMORY_WRITE)

    @server.tool(name="memory.search", annotations=ToolAnnotations(readOnlyHint=True))
    async def memory_search_cloud(
        query: Annotated[str, Field(min_length=1, max_length=MAX_QUERY_LENGTH)],
        space: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        type: MemoryType | None = None,
        state: MemoryState | None = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
        min_relevance: Annotated[float, Field(ge=0, le=1)] = 0.78,
    ) -> str:
        return await _call_cloud(runtime, "memory.search", locals(), Scope.MEMORY_READ)

    @server.tool(
        name="memory.update",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    )
    async def memory_update_cloud(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        expected_version: Annotated[int, Field(ge=1)],
        patch: MemoryPatch,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        provenance: Provenance | None = None,
    ) -> str:
        return await _call_cloud(runtime, "memory.update", locals(), Scope.MEMORY_WRITE)

    @server.tool(
        name="memory.forget",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
    )
    async def memory_forget_cloud(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        reason: Annotated[str | None, Field(max_length=256)] = None,
    ) -> str:
        return await _call_cloud(runtime, "memory.forget", locals(), Scope.MEMORY_DELETE)

    for tool in server._tool_manager._tools.values():
        tool.parameters["additionalProperties"] = False
    return server


def create_cloud_http_app(
    runtime: ServerRuntime,
    verifier: OIDCTokenVerifier,
    *,
    allowed_hosts: list[str] | None = None,
    admin_app: object | None = None,
    web_directory: Path | None = None,
) -> object:
    """Mount authenticated `/mcp` alongside redacted health/readiness routes.

    ``admin_app`` and ``web_directory`` are deliberately opt-in local composition
    inputs. They are installed before the MCP catch-all mount so a developer can
    exercise the Admin API and browser shell on the same origin without changing
    the hosted MCP contract.
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    server = create_cloud_server(runtime, verifier, allowed_hosts=allowed_hosts)

    @asynccontextmanager
    async def lifespan(_: object) -> AsyncIterator[None]:
        await runtime.startup()
        try:
            async with server.session_manager.run():
                yield
        finally:
            await runtime.close()

    app = FastAPI(
        title="UMCP Cloud",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def reject_client_owner_id(request: Request, call_next: object) -> object:
        """Reject, rather than silently discard, a hosted authorization boundary."""
        if request.method == "POST" and request.url.path == "/mcp":
            try:
                payload = json.loads((await request.body()).decode("utf-8"))
                arguments = payload.get("params", {}).get("arguments", {})
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                arguments = {}
            if isinstance(arguments, dict) and "owner_id" in arguments:
                return JSONResponse(
                    {"error": "invalid request"},
                    status_code=400,
                    headers={"cache-control": "no-store"},
                )
        return await cast(Any, call_next)(request)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        try:
            ready = await runtime.readiness()
        except BaseException:
            ready = False
        return JSONResponse({"status": "ready" if ready else "not_ready"}, 200 if ready else 503)

    if admin_app is not None:
        app.mount("/admin", cast(Any, admin_app))
    if web_directory is not None:
        if not web_directory.is_dir():
            raise ValueError("web_directory must be an existing directory")

        # This fixed, server-owned script supplies only an API path. It never
        # exposes a token, tenant, or other authorization input to the page.
        from fastapi.responses import Response

        @app.get("/web/admin-config.js", include_in_schema=False)
        async def local_web_admin_config() -> Response:
            return Response(
                'window.__UMCP_ADMIN_API_BASE_URL__ = "/admin";\n',
                media_type="application/javascript",
                headers={"cache-control": "no-store"},
            )

        app.mount("/web", StaticFiles(directory=str(web_directory), html=True), name="web")

    app.mount("/", server.streamable_http_app())
    return app


async def _call(runtime: ServerRuntime, name: str, values: dict[str, object]) -> str:
    arguments = {key: value for key, value in values.items() if key not in {"runtime", "name"}}
    envelope = await runtime.adapter.call_tool(name, arguments)
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


async def _call_cloud(
    runtime: ServerRuntime, name: str, values: dict[str, object], scope: Scope
) -> str:
    token = get_access_token()
    if token is None:
        raise PermissionError("authorization denied")
    principal = principal_from_access_token(token)
    principal.requires(scope)
    arguments = {
        key: value for key, value in values.items() if key not in {"runtime", "name", "scope"}
    }
    # Transitional compatibility mapping; it is derived only from verified
    # claims and cannot be selected by the hosted MCP caller.
    arguments["owner_id"] = f"cloud:{principal.tenant_id}:{principal.subject_id}"
    with tenant_scope(principal.tenant_id):
        envelope = await runtime.adapter.call_tool(name, arguments)
    _redact_hosted_owner(envelope)
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _redact_hosted_owner(value: object) -> None:
    if isinstance(value, dict):
        value.pop("owner_id", None)
        for child in value.values():
            _redact_hosted_owner(child)
    elif isinstance(value, list):
        for child in value:
            _redact_hosted_owner(child)


async def serve_stdio(runtime: ServerRuntime) -> None:
    server = create_official_server(runtime)
    try:
        await runtime.startup()
        await server.run_stdio_async()
    finally:
        await runtime.close()


def run_stdio(runtime: ServerRuntime) -> None:
    anyio.run(serve_stdio, runtime)
