"""In-process Streamable HTTP composition for the H03 local contract.

This module is an ASGI composition only: it does not bind a socket, verify
credentials, talk to a provider, or expose a public route. A caller must inject
an already verified Principal; that Principal is the sole source of tenant and
owner context.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from omp.cloud.security import Principal, Scope
from omp.cloud.tenant import tenant_scope

from .composition import ServerRuntime


class LocalSessionStore:
    def __init__(self) -> None:
        self._sessions: set[str] = set()

    def create(self) -> str:
        session = "mcp_" + uuid.uuid4().hex
        self._sessions.add(session)
        return session

    def known(self, session: str | None) -> bool:
        return bool(session and session in self._sessions)


def create_in_process_streamable_http_app(
    runtime: ServerRuntime,
    principal: Principal,
    *,
    readiness: Callable[[], bool | Awaitable[bool]] | None = None,
    allowed_hosts: tuple[str, ...] = ("testserver", "localhost", "127.0.0.1"),
) -> FastAPI:
    """Compose one exact `/mcp` route around the shared transport adapter."""

    sessions = LocalSessionStore()
    ready_check = readiness or (lambda: False)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await runtime.startup()
        try:
            yield
        finally:
            await runtime.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def host_boundary(request: Request, call_next: Any) -> Any:
        if request.url.path == "/mcp/":
            return JSONResponse({"error": "not found"}, status_code=404)
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        if host not in allowed_hosts:
            return JSONResponse({"error": "invalid host"}, status_code=400)
        return await call_next(request)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        try:
            value = ready_check()
            ready = await value if asyncio.iscoroutine(value) else bool(value)
        except BaseException:
            ready = False
        return JSONResponse({"status": "ready" if ready else "not_ready"}, 200 if ready else 503)

    @app.post("/mcp")
    async def mcp(request: Request) -> JSONResponse:
        request_id: Any = None
        try:
            payload = await request.json()
            request_id = payload.get("id") if isinstance(payload, dict) else None
            if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
                return _rpc_error(request_id, -32600, "invalid request")
            session = request.headers.get("mcp-session-id")
            method = payload.get("method")
            if method == "initialize":
                session = sessions.create()
                response = _rpc_result(
                    request_id,
                    {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "umcp-local", "version": "0.1"},
                    },
                )
                response.headers["mcp-session-id"] = session
                return response
            if not sessions.known(session):
                return _rpc_error(request_id, -32000, "session required", status=404)
            if method == "tools/list":
                return _rpc_result(request_id, {"tools": _tools()})
            if method == "tools/call":
                params = payload.get("params")
                if not isinstance(params, dict) or not isinstance(params.get("name"), str):
                    return _rpc_error(request_id, -32602, "invalid params")
                name = params["name"]
                arguments = params.get("arguments", {})
                if (
                    not isinstance(arguments, dict)
                    or "owner_id" in arguments
                    or "tenant_id" in arguments
                ):
                    return _rpc_error(request_id, -32602, "invalid params")
                scope = {
                    "memory.write": Scope.MEMORY_WRITE,
                    "memory.search": Scope.MEMORY_READ,
                    "memory.update": Scope.MEMORY_WRITE,
                    "memory.forget": Scope.MEMORY_DELETE,
                }.get(name)
                if scope is None:
                    return _rpc_error(request_id, -32602, "unknown tool")
                principal.requires(scope)
                injected = dict(arguments)
                injected["owner_id"] = f"cloud:{principal.tenant_id}:{principal.subject_id}"
                with tenant_scope(principal.tenant_id):
                    envelope = await runtime.adapter.call_tool(
                        name, injected, request_id=f"mcp:{request_id}"
                    )
                text = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
                return _rpc_result(request_id, {"content": [{"type": "text", "text": text}]})
            return _rpc_error(request_id, -32601, "method not found")
        except asyncio.CancelledError:
            raise
        except Exception:
            return _rpc_error(request_id, -32000, "request failed", status=503)

    return app


def _rpc_result(request_id: Any, result: Mapping[str, Any]) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


def _rpc_error(request_id: Any, code: int, message: str, *, status: int = 400) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}},
        status_code=status,
    )


def _tools() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": "UMCP memory tool",
            "inputSchema": {"type": "object", "additionalProperties": False},
        }
        for name in ("memory.write", "memory.search", "memory.update", "memory.forget")
    ]


__all__ = ["create_in_process_streamable_http_app"]
