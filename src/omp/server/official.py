"""Official MCP SDK server composition for the supported stdio transport."""

from __future__ import annotations

import json
import urllib.parse
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
from starlette.routing import BaseRoute, Match

from omp.adapters.mcp.http import (
    M1LocalAuth,
    create_m1_http_app,
    create_m1_server,
    create_m1_service,
)
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
from omp.config import OMPSettings
from .oauth import OAuthConfiguration, OAuthError, OAuthServer

from .composition import ServerRuntime, create_fail_closed_cloud_runtime


class _ExactMCPRoute(BaseRoute):
    """Delegate the public exact ``/mcp`` path to the Streamable HTTP ASGI app.

    Starlette's ``Mount`` intentionally matches a trailing slash, which means
    mounting at ``/mcp`` leaves the exact protocol endpoint as a 404 when the
    parent application has redirects disabled.  MCP clients use the endpoint
    without that slash, and a redirect can downgrade the scheme behind a TLS
    terminator.  This route rewrites only the child ASGI scope, keeping the
    externally visible path exact and leaving ``/mcp/`` unserved.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    def matches(self, scope: dict[str, Any]) -> tuple[Match, dict[str, Any]]:
        if scope["type"] == "http" and scope["path"] == "/mcp":
            return Match.FULL, scope
        return Match.NONE, {}

    async def handle(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        child_scope = dict(scope)
        child_scope["root_path"] = f"{scope.get('root_path', '')}/mcp"
        child_scope["path"] = "/"
        child_scope["raw_path"] = b"/"
        await self.app(child_scope, receive, send)


class RejectUnconfiguredOIDCVerifier:
    """Fail closed until deployment injects an approved hosted verifier."""

    async def verify_token(self, token: str) -> None:
        return None


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
    permitted_hosts = allowed_hosts or ["local.umcp.invalid"]
    server = FastMCP(
        name="umcp-cloud",
        instructions="Use memory tools only within the scopes granted to this integration.",
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=cast(AnyHttpUrl, "https://local.umcp.invalid"),
            resource_server_url=cast(AnyHttpUrl, "https://local.umcp.invalid/mcp"),
            required_scopes=[],
        ),
        # ``create_cloud_http_app`` mounts this ASGI application at the one
        # public MCP route.  The transport itself must therefore be rooted at
        # the mount point rather than declare a second ``/mcp`` segment.
        streamable_http_path="/",
        stateless_http=True,
        max_request_body_size=64 * 1024,
        transport_security=TransportSecuritySettings(
            allowed_hosts=permitted_hosts,
            allowed_origins=[f"https://{host}" for host in permitted_hosts],
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
    oauth_server: OAuthServer | None = None,
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
        # A hosted process must remain live when a required dependency is
        # unavailable so Cloud Run can expose a truthful readiness result and
        # recover when the dependency returns.  ``ServerRuntime.startup``
        # raises this specific error for an unavailable PostgreSQL backend;
        # MCP remains fail-closed because requests still pass through the
        # runtime and ``/readyz`` continues to report 503.
        try:
            await runtime.startup()
        except RuntimeError as exc:
            if str(exc) != "postgres readiness check failed":
                raise
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
        redirect_slashes=False,
    )

    @app.middleware("http")
    async def add_provenance_headers(request: Request, call_next: object) -> object:
        response: Any = await cast(Any, call_next)(request)
        if runtime.settings.image_digest:
            response.headers["X-UMCP-Image-Digest"] = runtime.settings.image_digest
        if runtime.settings.image_source_sha:
            response.headers["X-UMCP-Image-Source-SHA"] = runtime.settings.image_source_sha
        return response

    @app.middleware("http")
    async def reject_client_owner_id(request: Request, call_next: object) -> object:
        """Reject, rather than silently discard, a hosted authorization boundary."""
        if request.url.path == "/mcp/":
            return JSONResponse(
                {"error": "not found"}, status_code=404, headers={"cache-control": "no-store"}
            )
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

    if oauth_server is not None:
        @app.get("/.well-known/oauth-protected-resource")
        async def protected_metadata() -> dict[str, object]:
            return {"resource": oauth_server.config.issuer + "/mcp", "authorization_servers": [oauth_server.config.issuer], "scopes_supported": sorted({"memory:read", "memory:write", "memory:delete"})}

        @app.get("/.well-known/oauth-protected-resource/mcp")
        async def protected_mcp_metadata() -> dict[str, object]:
            return await protected_metadata()

        @app.get("/.well-known/oauth-authorization-server")
        async def authorization_metadata() -> dict[str, object]:
            return oauth_server.metadata()

        @app.get("/authorize")
        @app.get("/oauth/authorize")
        async def authorize(response_type: str, client_id: str, redirect_uri: str, scope: str, state: str, code_challenge: str, code_challenge_method: str) -> object:
            if response_type != "code":
                return JSONResponse({"error": "unsupported_response_type"}, 400)
            try:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(await oauth_server.begin(client_id, redirect_uri, scope, state, code_challenge, code_challenge_method), status_code=302)
            except OAuthError as exc:
                return JSONResponse({"error": exc.code}, exc.status)

        @app.get("/oauth/callback")
        async def oauth_callback(code: str = "", state: str = "") -> object:
            try:
                redirect_uri, authorization_code, client_state = await oauth_server.callback(code, state)
                query = urllib.parse.urlencode({"code": authorization_code, "state": client_state})
                from fastapi.responses import RedirectResponse
                return RedirectResponse(redirect_uri + ("&" if "?" in redirect_uri else "?") + query, status_code=302)
            except OAuthError as exc:
                return JSONResponse({"error": exc.code}, exc.status)

        @app.post("/token")
        async def token(request: Request) -> object:
            try:
                body = (await request.body()).decode("utf-8")
                form = dict(urllib.parse.parse_qsl(body, keep_blank_values=True))
                return JSONResponse(await oauth_server.token(form), headers={"cache-control": "no-store", "pragma": "no-cache"})
            except UnicodeDecodeError:
                return JSONResponse({"error": "invalid_request"}, 400, headers={"cache-control": "no-store"})
            except OAuthError as exc:
                return JSONResponse({"error": exc.code}, exc.status, headers={"cache-control": "no-store"})

        @app.post("/revoke")
        async def revoke(request: Request) -> object:
            try:
                form = dict(urllib.parse.parse_qsl((await request.body()).decode("utf-8")))
            except UnicodeDecodeError:
                return JSONResponse({"error": "invalid_request"}, 400, headers={"cache-control": "no-store"})
            await oauth_server.revoke(form.get("token", ""))
            return JSONResponse({}, 200, headers={"cache-control": "no-store"})

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

    # This must be registered after the non-MCP routes, while still matching
    # the exact public endpoint rather than Starlette's trailing-slash mount.
    app.router.routes.append(_ExactMCPRoute(server.streamable_http_app()))
    return app


def create_fail_closed_cloud_http_app(settings: OMPSettings | None = None) -> object:
    """Compose the image entrypoint as hosted MCP, never as local M1.

    This is intentionally non-serving for credentials until an approved OIDC
    verifier is wired outside this local remediation.  Its public surface is
    still the hosted ``/mcp`` composition, including exact-path handling.
    """
    runtime = create_fail_closed_cloud_runtime(settings)
    config = OAuthConfiguration.from_settings(runtime.settings)
    if config is None or runtime.engine is None:
        return create_cloud_http_app(runtime, RejectUnconfiguredOIDCVerifier())
    oauth = OAuthServer(runtime.engine, config)
    return create_cloud_http_app(runtime, oauth, oauth_server=oauth)


__all__ = [
    "create_cloud_http_app",
    "create_fail_closed_cloud_http_app",
    "create_cloud_server",
    "create_m1_http_app",
    "create_m1_server",
    "create_m1_service",
    "M1LocalAuth",
]


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
