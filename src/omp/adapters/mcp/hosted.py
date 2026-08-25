"""Hosted trust-boundary adapter, deliberately separate from local MCP mode.

The HTTP surface here is a narrow, internal composition seam for adversarial
tests.  It is not an OAuth implementation or a public Streamable HTTP server;
the production MCP runtime will compose this adapter only after an approved
identity-provider integration exists.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omp.adapters.mcp.schemas import MAX_CONTENT_LENGTH, MAX_LIMIT, MAX_QUERY_LENGTH, MemoryPatch
from omp.server.hosted_auth import HostedAuthenticationError, HostedAuthenticator, Principal


class HostedBoundaryError(ValueError):
    """Safe request error for the hosted edge."""

    def __init__(self, code: str, *, status_code: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class HostedStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HostedWriteArguments(HostedStrictModel):
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)
    type: str = Field(min_length=1, max_length=32)
    provenance: dict[str, Any]
    idempotency_key: str = Field(min_length=1, max_length=128)
    space: str | None = Field(default=None, min_length=1, max_length=128)
    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)


class HostedSearchArguments(HostedStrictModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    space: str | None = Field(default=None, min_length=1, max_length=128)
    type: str | None = Field(default=None, min_length=1, max_length=32)
    state: str | None = Field(default=None, min_length=1, max_length=32)
    limit: int = Field(default=10, ge=1, le=MAX_LIMIT)
    min_relevance: float = Field(default=0.78, ge=0, le=1)


class HostedUpdateArguments(HostedStrictModel):
    id: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=1)
    patch: MemoryPatch
    idempotency_key: str = Field(min_length=1, max_length=128)
    provenance: dict[str, Any] | None = None


class HostedForgetArguments(HostedStrictModel):
    id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=256)


_TOOL_SCOPES = {
    "memory.write": "memory:write",
    "memory.search": "memory:read",
    "memory.update": "memory:write",
    "memory.forget": "memory:delete",
}
_TOOL_MODELS: dict[str, type[HostedStrictModel]] = {
    "memory.write": HostedWriteArguments,
    "memory.search": HostedSearchArguments,
    "memory.update": HostedUpdateArguments,
    "memory.forget": HostedForgetArguments,
}


@dataclass(frozen=True, slots=True)
class HostedToolCall:
    """The only hosted command shape handed to a persistence-facing service."""

    tool_name: str
    principal: Principal
    arguments: Mapping[str, Any]


class HostedMemoryService(Protocol):
    def call(self, command: HostedToolCall) -> dict[str, Any]: ...


class HostedMCPAdapter:
    """Authenticate before validating or dispatching a hosted tool call."""

    def __init__(self, service: HostedMemoryService, authenticator: HostedAuthenticator) -> None:
        self._service = service
        self._authenticator = authenticator

    async def call_tool(
        self,
        *,
        authorization: str | None,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        principal = await self.authenticate(authorization=authorization, tool_name=tool_name)
        return await self._call_authenticated_tool(
            tool_name=tool_name, principal=principal, arguments=arguments
        )

    async def authenticate(self, *, authorization: str | None, tool_name: str) -> Principal:
        required_scope = _TOOL_SCOPES.get(tool_name)
        if required_scope is None:
            raise HostedBoundaryError("unknown_tool", status_code=404)
        return await self._authenticator.authenticate(authorization, required_scope=required_scope)

    async def _call_authenticated_tool(
        self, *, tool_name: str, principal: Principal, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        try:
            validated = _TOOL_MODELS[tool_name].model_validate(dict(arguments))
        except (TypeError, ValidationError) as exc:
            raise HostedBoundaryError("invalid_request") from exc
        command = HostedToolCall(
            tool_name=tool_name,
            principal=principal,
            arguments=validated.model_dump(mode="json", exclude_none=True),
        )
        try:
            result = self._service.call(command)
            if inspect.isawaitable(result):
                result = await result
        except HostedBoundaryError:
            raise
        except Exception as exc:
            raise HostedBoundaryError("service_unavailable", status_code=503) from exc
        if not isinstance(result, dict):
            raise HostedBoundaryError("service_unavailable", status_code=503)
        return result


def create_hosted_boundary_app(adapter: HostedMCPAdapter) -> FastAPI:
    """Create an internal HTTP composition for exercising hosted trust rules.

    ``/_hosted_boundary`` is intentionally not the public ``/mcp`` transport.
    It exists so the identity boundary is testable before IdP and MCP runtime
    selection are authorized.
    """

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.post("/_hosted_boundary/{tool_name}")
    async def call_hosted_tool(tool_name: str, request: Request) -> JSONResponse:
        try:
            principal = await adapter.authenticate(
                authorization=request.headers.get("authorization"), tool_name=tool_name
            )
            try:
                arguments = await request.json()
            except (TypeError, ValueError):
                arguments = None
            if not isinstance(arguments, dict):
                raise HostedBoundaryError("invalid_request")
            result = await adapter._call_authenticated_tool(
                tool_name=tool_name,
                principal=principal,
                arguments=arguments,
            )
            return JSONResponse({"ok": True, "data": result}, headers={"cache-control": "no-store"})
        except HostedAuthenticationError as exc:
            return _error_response(exc.code, exc.status_code)
        except HostedBoundaryError as exc:
            return _error_response(exc.code, exc.status_code)

    return app


def _error_response(code: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": {"code": code}},
        status_code=status_code,
        headers={"cache-control": "no-store"},
    )


__all__ = [
    "HostedBoundaryError",
    "HostedMCPAdapter",
    "HostedMemoryService",
    "HostedToolCall",
    "create_hosted_boundary_app",
]
