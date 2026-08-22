"""M1 local Streamable HTTP composition.

This module is deliberately a transport adapter.  It derives the application
scope from a local, test-only bearer-token registry and maps the eight frozen
M1 tools to ``MemoryApplicationService``.  It does not add business rules to
the Core service and the revoke/restore endpoints are HTTP controls, not MCP
tools.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any, Final

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.requests import Request
from starlette.responses import JSONResponse

from omp.adapters.embeddings import HashEmbeddingProvider
from omp.application.fakes import InMemoryUnitOfWorkFactory
from omp.application.models import (
    CaptureMemoryCommand,
    ConfirmCandidateCommand,
    DiscardCandidateCommand,
    ForgetMemoryCommand,
    ListInboxCommand,
    PinMemoryCommand,
    RecallMemoryCommand,
    SpacePolicy,
    UpdateMemoryCommand,
)
from omp.application.services import MemoryApplicationService
from omp.domain import (
    CaptureConsent,
    ConsentMode,
    ConsentReason,
    MemoryState,
    MemoryType,
    Provenance,
    SourceType,
)

M1_PROTOCOL = "omp.mcp.m1"
M1_MAX_CONTENT = 16_384
M1_MAX_QUERY = 4_096
M1_MAX_LIMIT = 50
M1_MAX_SPACE = 128
M1_MAX_IDEMPOTENCY = 128
M1_ALLOWED_SCOPES: Final[frozenset[str]] = frozenset(
    {"memory:read", "memory:write", "memory:delete"}
)


class M1StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, validate_assignment=True, use_enum_values=True
    )


class M1Provenance(M1StrictModel):
    source_type: str = Field(min_length=1, max_length=32)
    source_client: str = Field(min_length=1, max_length=128)
    source_connection_id: str | None = Field(default=None, max_length=256)
    conversation_id: str | None = Field(default=None, max_length=256)
    message_id: str | None = Field(default=None, max_length=256)
    source_model: str | None = Field(default=None, max_length=128)
    captured_at: str = Field(min_length=1, max_length=80)
    evidence: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("captured_at")
    @classmethod
    def normalize_timestamp(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("captured_at must be an RFC 3339 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


class M1Consent(M1StrictModel):
    mode: str = Field(min_length=1, max_length=32)
    consent_id: str = Field(min_length=1, max_length=256)
    reason_code: str = Field(min_length=1, max_length=64)
    policy_version: str = Field(min_length=1, max_length=128)
    granted_at: str = Field(min_length=1, max_length=80)

    @field_validator("granted_at")
    @classmethod
    def normalize_timestamp(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("granted_at must be an RFC 3339 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("granted_at must include a timezone")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


class M1Patch(M1StrictModel):
    content: str | None = Field(default=None, min_length=1, max_length=M1_MAX_CONTENT)
    type: str | None = Field(default=None, min_length=1, max_length=32)
    space: str | None = Field(default=None, min_length=1, max_length=M1_MAX_SPACE)
    importance: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    state: str | None = Field(default=None, min_length=1, max_length=32)
    provenance: M1Provenance | None = None

    @field_validator("content")
    @classmethod
    def non_blank_content(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("content must not be blank")
        return value

    @model_validator(mode="after")
    def has_change(self) -> M1Patch:
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("patch must contain at least one change")
        return self


class M1RevokeRequest(M1StrictModel):
    connection_id: str = Field(min_length=1, max_length=256)
    client: str = Field(min_length=1, max_length=128)


class M1RestoreRequest(M1StrictModel):
    format: str
    exported_at: str = Field(min_length=1, max_length=80)
    includes_embeddings: bool = False
    memories: list[dict[str, Any]] = Field(max_length=100)


@dataclass(slots=True)
class M1Principal:
    name: str
    tenant_id: str
    owner_id: str
    connection_id: str
    client_id: str
    scopes: frozenset[str]
    allowed_spaces: frozenset[str] = frozenset({"MBA", "Work"})
    revoked: bool = False


class M1LocalAuth:
    """Local-only token registry with trusted synthetic principals.

    Tokens are opaque bearer values.  They are never accepted from request
    arguments and are never included in responses or logs.
    """

    def __init__(self, principals: Iterable[tuple[str, M1Principal]] | None = None) -> None:
        self._tokens: dict[str, M1Principal] = {}
        self._connections: dict[tuple[str, str], M1Principal] = {}
        values = tuple(principals) if principals is not None else self._defaults()
        for token, principal in values:
            self.register(token, principal)

    def register(self, token: str, principal: M1Principal) -> None:
        if not token.strip():
            raise ValueError("local token must be non-empty")
        self._tokens[token] = principal
        self._connections[(principal.tenant_id, principal.connection_id)] = principal

    async def verify_token(self, token: str) -> Any | None:
        principal = self._tokens.get(token)
        if principal is None:
            return None
        from mcp.server.auth.provider import AccessToken

        # FastMCP performs authentication before invoking a tool.  The
        # connection's revoked flag is intentionally checked in every tool,
        # so an already-issued token can receive a safe connection_revoked
        # result instead of leaking a different authentication outcome.
        return AccessToken(
            token=token,
            client_id=principal.client_id,
            scopes=sorted(principal.scopes),
            expires_at=int(datetime.now(UTC).timestamp()) + 3600,
            resource="https://m1.local.invalid/mcp",
            subject=principal.owner_id,
            claims={
                "tenant_id": principal.tenant_id,
                "connection_id": principal.connection_id,
                "client_id": principal.client_id,
            },
        )

    def principal_from_request(self, request: Request) -> M1Principal | None:
        value = request.headers.get("authorization", "")
        scheme, _, token = value.partition(" ")
        if scheme.casefold() != "bearer" or not token:
            return None
        return self._tokens.get(token)

    def principal_from_mcp(self) -> M1Principal:
        token = get_access_token()
        if token is None:
            raise PermissionError("authorization denied")
        principal = self._tokens.get(token.token)
        if principal is None:
            raise PermissionError("authorization denied")
        return principal

    def revoke(self, *, actor: M1Principal, connection_id: str, client: str) -> None:
        target = self._connections.get((actor.tenant_id, connection_id))
        if target is None or target.client_id != client:
            raise PermissionError("operation not permitted")
        target.revoked = True

    def _defaults(self) -> tuple[tuple[str, M1Principal], ...]:
        return (
            self._default(
                "M1_TOKEN_CHATGPT_SIM",
                "m1-fixture-chatgpt-sim",
                "chatgpt-sim",
                "tenant-a",
                "user-a",
                "conn-chatgpt-sim",
            ),
            self._default(
                "M1_TOKEN_CLAUDE_SIM",
                "m1-fixture-claude-sim",
                "claude-sim",
                "tenant-a",
                "user-a",
                "conn-claude-sim",
            ),
            self._default(
                "M1_TOKEN_CHATGPT_SIM_B",
                "m1-fixture-chatgpt-sim-b",
                "chatgpt-sim-b",
                "tenant-b",
                "user-b",
                "conn-chatgpt-sim-b",
            ),
        )

    @staticmethod
    def _default(
        variable: str, fallback: str, name: str, tenant: str, user: str, connection: str
    ) -> tuple[str, M1Principal]:
        token = os.getenv(variable, fallback).strip()
        return token, M1Principal(
            name=name,
            tenant_id=tenant,
            owner_id=f"m1:{tenant}:{user}",
            connection_id=connection,
            client_id=name,
            scopes=M1_ALLOWED_SCOPES,
        )


@dataclass(slots=True)
class M1LocalControl:
    service: MemoryApplicationService
    auth: M1LocalAuth
    tombstones: set[tuple[str, str, str]] = field(default_factory=set)

    async def is_tombstoned(self, principal: M1Principal, memory_id: str) -> bool:
        key = (principal.tenant_id, principal.owner_id, memory_id)
        if key in self.tombstones:
            return True
        factory = getattr(self.service, "_uow_factory", None)
        if factory is None:
            return False
        try:
            target = uuid.UUID(memory_id)
        except ValueError:
            return False
        try:
            async with factory() as uow:
                return bool(
                    await uow.admin.is_tombstoned(
                        owner_id=principal.owner_id,
                        memory_id=target,
                        tenant_id=principal.tenant_id,
                    )
                )
        except (AttributeError, TypeError, ValueError):
            return False


def create_m1_service() -> MemoryApplicationService:
    """Create the explicit synthetic local Core composition."""
    return MemoryApplicationService(
        uow_factory=InMemoryUnitOfWorkFactory(),
        embedding_provider=HashEmbeddingProvider(),
    )


def create_m1_server(
    service: MemoryApplicationService,
    auth: M1LocalAuth,
    control: M1LocalControl | None = None,
    *,
    allowed_hosts: list[str] | None = None,
) -> FastMCP:
    control = control or M1LocalControl(service=service, auth=auth)
    server = FastMCP(
        name="open-memory-protocol",
        instructions="Use only the authenticated local memory tools; empty recall is valid.",
        token_verifier=auth,
        auth=AuthSettings(
            issuer_url="https://m1.local.invalid",
            resource_server_url="https://m1.local.invalid/mcp",
            required_scopes=[],
        ),
        streamable_http_path="/mcp",
        stateless_http=True,
        max_request_body_size=64 * 1024,
        transport_security=TransportSecuritySettings(
            allowed_hosts=allowed_hosts
            or ["127.0.0.1", "localhost", "testserver", "m1.local.invalid"]
        ),
    )

    @server.tool(
        name="memory.capture",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    )
    async def memory_capture(
        content: Annotated[str, Field(min_length=1, max_length=M1_MAX_CONTENT)],
        type: Annotated[str, Field(min_length=1, max_length=32)],
        space: Annotated[str | None, Field(min_length=1, max_length=M1_MAX_SPACE)],
        provenance: M1Provenance,
        consent: M1Consent,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=M1_MAX_IDEMPOTENCY)],
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control,
            principal,
            "memory.capture",
            content=content,
            type=type,
            space=space,
            provenance=provenance,
            consent=consent,
            idempotency_key=idempotency_key,
        )

    @server.tool(
        name="memory.inbox.list",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    )
    async def memory_inbox_list(
        space: Annotated[str | None, Field(min_length=1, max_length=M1_MAX_SPACE)] = None,
        limit: Annotated[int, Field(ge=1, le=M1_MAX_LIMIT)] = M1_MAX_LIMIT,
        cursor: Annotated[str | None, Field(max_length=128)] = None,
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control, principal, "memory.inbox.list", space=space, limit=limit, cursor=cursor
        )

    @server.tool(
        name="memory.inbox.confirm",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    )
    async def memory_inbox_confirm(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        expected_version: Annotated[int, Field(ge=1)],
        idempotency_key: Annotated[str, Field(min_length=1, max_length=M1_MAX_IDEMPOTENCY)],
        patch: M1Patch | None = None,
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control,
            principal,
            "memory.inbox.confirm",
            id=id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            patch=patch,
        )

    @server.tool(
        name="memory.inbox.discard",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
    )
    async def memory_inbox_discard(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        expected_version: Annotated[int, Field(ge=1)],
        idempotency_key: Annotated[str, Field(min_length=1, max_length=M1_MAX_IDEMPOTENCY)],
        reason_code: Annotated[str | None, Field(max_length=64)] = None,
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control,
            principal,
            "memory.inbox.discard",
            id=id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            reason_code=reason_code,
        )

    @server.tool(
        name="memory.pin",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    )
    async def memory_pin(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        expected_version: Annotated[int, Field(ge=1)],
        pinned: bool,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=M1_MAX_IDEMPOTENCY)],
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control,
            principal,
            "memory.pin",
            id=id,
            expected_version=expected_version,
            pinned=pinned,
            idempotency_key=idempotency_key,
        )

    @server.tool(
        name="memory.recall",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    )
    async def memory_recall(
        query: Annotated[str, Field(min_length=1, max_length=M1_MAX_QUERY)],
        context_space: Annotated[str | None, Field(min_length=1, max_length=M1_MAX_SPACE)],
        include_spaces: list[str] | None = None,
        types: list[str] | None = None,
        states: list[str] | None = None,
        allow_mental_notes: bool = False,
        limit: Annotated[int, Field(ge=1, le=M1_MAX_LIMIT)] = 5,
        # The dependency-free local hash profile is intentionally conservative
        # but not semantic; this calibrated floor keeps the synthetic journey
        # reproducible without downloading a model.
        threshold: Annotated[float, Field(ge=0, le=1)] = 0.65,
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control,
            principal,
            "memory.recall",
            query=query,
            context_space=context_space,
            include_spaces=include_spaces,
            types=types,
            states=states,
            allow_mental_notes=allow_mental_notes,
            limit=limit,
            threshold=threshold,
        )

    @server.tool(
        name="memory.update",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    )
    async def memory_update(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        expected_version: Annotated[int, Field(ge=1)],
        patch: M1Patch,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=M1_MAX_IDEMPOTENCY)],
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control,
            principal,
            "memory.update",
            id=id,
            expected_version=expected_version,
            patch=patch,
            idempotency_key=idempotency_key,
        )

    @server.tool(
        name="memory.forget",
        structured_output=False,
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
    )
    async def memory_forget(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        idempotency_key: Annotated[str, Field(min_length=1, max_length=M1_MAX_IDEMPOTENCY)],
        reason_code: Annotated[str | None, Field(max_length=64)] = None,
    ) -> str:
        principal = auth.principal_from_mcp()
        return await _invoke(
            control,
            principal,
            "memory.forget",
            id=id,
            idempotency_key=idempotency_key,
            reason_code=reason_code,
        )

    for tool in server._tool_manager._tools.values():
        tool.parameters["additionalProperties"] = False

    # FastMCP's generated argument model currently drops unknown top-level
    # keys before invoking the function. Preserve the frozen strict-schema
    # behavior at runtime as well, returning the same safe JSON envelope that
    # a normal M1 tool error uses.
    original_call_tool = server._tool_manager.call_tool

    async def strict_call_tool(
        name: str,
        arguments: dict[str, Any],
        context: Any = None,
        convert_result: bool = False,
    ) -> Any:
        tool = server._tool_manager.get_tool(name)
        if tool is not None:
            allowed = set(tool.parameters.get("properties", {}))
            if set(arguments) - allowed:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=_error("req_" + uuid.uuid4().hex, "validation_error"),
                        )
                    ],
                    isError=True,
                )
        try:
            return await original_call_tool(
                name, arguments, context=context, convert_result=convert_result
            )
        except Exception:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=_error("req_" + uuid.uuid4().hex, "validation_error"),
                    )
                ],
                isError=True,
            )

    server._tool_manager.call_tool = strict_call_tool  # type: ignore[method-assign]
    return server


def create_m1_http_app(
    service: MemoryApplicationService | None = None,
    *,
    auth: M1LocalAuth | None = None,
    allowed_hosts: list[str] | None = None,
) -> Any:
    """Create the local authenticated M1 HTTP app.

    The default composition is synthetic and in-memory.  A caller may inject
    the real Core application service for a local PostgreSQL composition.
    """
    from fastapi import FastAPI

    selected_service = service or create_m1_service()
    selected_auth = auth or M1LocalAuth()
    control = M1LocalControl(selected_service, selected_auth)
    server = create_m1_server(selected_service, selected_auth, control, allowed_hosts=allowed_hosts)

    @asynccontextmanager
    async def lifespan(_: object):
        async with server.session_manager.run():
            yield

    app = FastAPI(
        title="UMCP M1 local", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
    )
    app.state.m1_server = server
    app.state.m1_control = control

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    async def revoke(request: Request) -> JSONResponse:
        principal = selected_auth.principal_from_request(request)
        if principal is None:
            return JSONResponse({"error": "authorization denied"}, status_code=401)
        try:
            payload = M1RevokeRequest.model_validate(await request.json())
            selected_auth.revoke(
                actor=principal, connection_id=payload.connection_id, client=payload.client
            )
        except Exception:
            return JSONResponse({"error": "operation not permitted"}, status_code=403)
        return JSONResponse({"status": "revoked"})

    async def restore(request: Request) -> JSONResponse:
        principal = selected_auth.principal_from_request(request)
        if principal is None:
            return JSONResponse({"error": "authorization denied"}, status_code=401)
        try:
            payload = M1RestoreRequest.model_validate(await request.json())
            if payload.format != "omp.export.v0" or len(payload.memories) != 1:
                raise ValueError("invalid restore package")
            memory_id = payload.memories[0].get("id")
            if not isinstance(memory_id, str) or not await control.is_tombstoned(
                principal, memory_id
            ):
                return JSONResponse({"status": "validation_error"}, status_code=400)
        except Exception:
            return JSONResponse({"status": "validation_error"}, status_code=400)
        return JSONResponse({"status": "restore_blocked_by_tombstone"})

    # Stable local-control paths.  Aliases are kept inside the local adapter
    # only so a runner can configure either endpoint without changing MCP.
    for path in ("/local/revoke", "/m1/revoke"):
        app.add_api_route(path, revoke, methods=["POST"], include_in_schema=False)
    for path in ("/local/restore", "/m1/restore"):
        app.add_api_route(path, restore, methods=["POST"], include_in_schema=False)

    app.mount("/", server.streamable_http_app())
    return app


async def _invoke(control: M1LocalControl, principal: M1Principal, name: str, **values: Any) -> str:
    request_id = "req_" + uuid.uuid4().hex
    try:
        if principal.revoked:
            raise _M1BoundaryError("connection_revoked")
        required_scope = (
            "memory:delete"
            if name in {"memory.forget", "memory.inbox.discard"}
            else "memory:read"
            if name in {"memory.recall", "memory.inbox.list"}
            else "memory:write"
        )
        if required_scope not in principal.scopes:
            raise _M1BoundaryError("scope_denied")
        owner_id = principal.owner_id
        tenant_id = principal.tenant_id
        if name == "memory.capture":
            provenance = values["provenance"]
            if provenance.source_client != principal.client_id:
                raise _M1BoundaryError("validation_error")
            if (
                provenance.source_connection_id is not None
                and provenance.source_connection_id != principal.connection_id
            ):
                raise _M1BoundaryError("validation_error")
            if values["space"] is not None and values["space"] not in principal.allowed_spaces:
                raise _M1BoundaryError("space_forbidden")
            result = await control.service.capture(
                CaptureMemoryCommand(
                    tenant_id=tenant_id,
                    owner_id=owner_id,
                    connection_id=principal.connection_id,
                    content=values["content"],
                    memory_type=MemoryType(values["type"]),
                    space=values["space"],
                    provenance=_provenance(values["provenance"]),
                    consent=_consent(values["consent"]),
                    idempotency_key=values["idempotency_key"],
                    connection_revoked=principal.revoked,
                    scopes=principal.scopes,
                )
            )
            return _ok(
                request_id,
                {
                    "memory": _memory(result.memory),
                    "status": "created" if result.created else "already_exists",
                },
            )
        if name == "memory.inbox.list":
            result = await control.service.list_inbox(
                ListInboxCommand(
                    tenant_id,
                    owner_id,
                    principal.connection_id,
                    space=values["space"],
                    limit=values["limit"],
                    cursor=values["cursor"],
                    scopes=principal.scopes,
                )
            )
            return _ok(
                request_id,
                {
                    "candidates": [_memory(item) for item in result.candidates],
                    "count": len(result.candidates),
                    "next_cursor": result.next_cursor,
                },
            )
        if name == "memory.inbox.confirm":
            patch = values["patch"]
            memory = await control.service.confirm_candidate(
                ConfirmCandidateCommand(
                    tenant_id,
                    owner_id,
                    principal.connection_id,
                    _uuid(values["id"]),
                    values["expected_version"],
                    values["idempotency_key"],
                    content=patch.content if patch else None,
                    memory_type=MemoryType(patch.type) if patch and patch.type else None,
                    space=patch.space if patch else None,
                    connection_revoked=principal.revoked,
                    scopes=principal.scopes,
                )
            )
            return _ok(request_id, {"memory": _memory(memory), "status": "confirmed"})
        if name == "memory.inbox.discard":
            result = await control.service.discard_candidate(
                DiscardCandidateCommand(
                    tenant_id,
                    owner_id,
                    principal.connection_id,
                    _uuid(values["id"]),
                    values["expected_version"],
                    values["idempotency_key"],
                    reason_code=values["reason_code"] or "user_requested_memory",
                    connection_revoked=principal.revoked,
                    scopes=principal.scopes,
                )
            )
            if result.forgotten:
                control.tombstones.add((tenant_id, owner_id, str(result.memory_id)))
            return _ok(
                request_id, {"status": "forgotten" if result.forgotten else "already_absent"}
            )
        if name == "memory.pin":
            memory = await control.service.pin(
                PinMemoryCommand(
                    tenant_id,
                    owner_id,
                    principal.connection_id,
                    _uuid(values["id"]),
                    values["expected_version"],
                    values["pinned"],
                    values["idempotency_key"],
                    connection_revoked=principal.revoked,
                    scopes=principal.scopes,
                )
            )
            return _ok(request_id, {"memory": _memory(memory), "status": memory.state.value})
        if name == "memory.recall":
            include = tuple(values["include_spaces"] or ())
            requested = tuple(MemoryType(item) for item in (values["types"] or ())) or None
            states = frozenset(MemoryState(item) for item in (values["states"] or ())) or frozenset(
                {MemoryState.CONFIRMED, MemoryState.PINNED}
            )
            policy = SpacePolicy(
                default_recall="explicit_allowlist" if include else "same_space_only",
                allowed_spaces=principal.allowed_spaces,
            )
            result = await control.service.recall(
                RecallMemoryCommand(
                    tenant_id,
                    owner_id,
                    principal.connection_id,
                    values["query"],
                    values["context_space"],
                    include_spaces=include,
                    memory_types=requested,
                    states=states,
                    allow_mental_notes=values["allow_mental_notes"],
                    limit=values["limit"],
                    threshold=values["threshold"],
                    space_policy=policy,
                    connection_revoked=principal.revoked,
                    scopes=principal.scopes,
                )
            )
            memories = [
                {
                    **_memory(item.memory),
                    "score": item.score,
                    "reason_retrieved": item.reason_retrieved,
                    "profile_id": item.profile_id,
                    "profile_version": item.profile_version,
                }
                for item in result.items
            ]
            return _ok(request_id, {"memories": memories, "count": result.count})
        if name == "memory.update":
            patch = values["patch"]
            memory = await control.service.update(
                UpdateMemoryCommand(
                    owner_id,
                    _uuid(values["id"]),
                    values["expected_version"],
                    content=patch.content,
                    memory_type=MemoryType(patch.type) if patch.type else None,
                    importance=patch.importance,
                    confidence=patch.confidence,
                    state=MemoryState(patch.state) if patch.state else None,
                    space=patch.space,
                    provenance=_provenance(patch.provenance) if patch.provenance else None,
                    idempotency_key=values["idempotency_key"],
                )
            )
            return _ok(request_id, {"memory": _memory(memory), "status": "updated"})
        if name == "memory.forget":
            result = await control.service.forget(
                ForgetMemoryCommand(
                    owner_id,
                    _uuid(values["id"]),
                    values["idempotency_key"],
                    reason_code=values["reason_code"] or "user_requested_memory",
                    tenant_id=tenant_id,
                )
            )
            if result.forgotten:
                control.tombstones.add((tenant_id, owner_id, str(result.memory_id)))
            return _ok(
                request_id, {"status": "forgotten" if result.forgotten else "already_absent"}
            )
        raise _M1BoundaryError("validation_error")
    except Exception as error:
        return _error(request_id, _safe_code(error))


class _M1BoundaryError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def _safe_code(error: BaseException) -> str:
    code = getattr(error, "code", None)
    if isinstance(error, _M1BoundaryError):
        return error.code
    if code in {
        "validation_error",
        "not_found",
        "version_conflict",
        "invalid_state_transition",
        "idempotency_conflict",
        "idempotency_in_progress",
        "consent_required",
        "capture_disabled",
        "connection_revoked",
        "scope_denied",
        "space_forbidden",
        "restore_blocked_by_tombstone",
        "relation_conflict",
        "storage_error",
    }:
        return str(code)
    if isinstance(error, ValueError | TypeError | KeyError):
        return "validation_error"
    if isinstance(error, TimeoutError):
        return "storage_error"
    return "storage_error"


def _ok(request_id: str, data: dict[str, Any]) -> str:
    return json.dumps(
        {"protocol_version": M1_PROTOCOL, "request_id": request_id, "ok": True, "data": data},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _error(request_id: str, code: str) -> str:
    return json.dumps(
        {
            "protocol_version": M1_PROTOCOL,
            "request_id": request_id,
            "ok": False,
            "error": {
                "code": code,
                "message": "memory operation could not be completed",
                "retryable": code in {"idempotency_in_progress", "storage_error"},
            },
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _provenance(value: M1Provenance | None) -> Provenance:
    if value is None:
        raise ValueError("provenance is required")
    return Provenance(
        source_type=SourceType(value.source_type),
        source_client=value.source_client,
        source_connection_id=value.source_connection_id,
        conversation_id=value.conversation_id,
        message_id=value.message_id,
        source_model=value.source_model,
        captured_at=datetime.fromisoformat(value.captured_at.replace("Z", "+00:00")),
        evidence=tuple(value.evidence),
    )


def _consent(value: M1Consent) -> CaptureConsent:
    return CaptureConsent(
        mode=ConsentMode(value.mode),
        consent_id=value.consent_id,
        reason_code=ConsentReason(value.reason_code),
        policy_version=value.policy_version,
        granted_at=datetime.fromisoformat(value.granted_at.replace("Z", "+00:00")),
    )


def _timestamp(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def _memory(value: Any) -> dict[str, Any]:
    provenance = value.provenance
    result: dict[str, Any] = {
        "id": str(value.id),
        "content": value.content,
        "type": value.memory_type.value,
        "space": value.space,
        "importance": value.importance,
        "confidence": value.confidence,
        "state": value.state.value,
        "version": value.version,
        "created_at": _timestamp(value.created_at),
        "updated_at": _timestamp(value.updated_at),
        "occurred_at": _timestamp(value.occurred_at),
        "provenance": {
            "source_type": provenance.source_type.value,
            "source_client": provenance.source_client,
            "source_connection_id": provenance.source_connection_id,
            "conversation_id": provenance.conversation_id,
            "message_id": provenance.message_id,
            "source_model": provenance.source_model,
            "captured_at": _timestamp(provenance.captured_at),
            "evidence": list(provenance.evidence),
        },
    }
    if value.capture_consent is not None:
        result["capture_consent"] = {
            "mode": value.capture_consent.mode.value,
            "consent_id": value.capture_consent.consent_id,
            "reason_code": value.capture_consent.reason_code.value,
            "policy_version": value.capture_consent.policy_version,
            "granted_at": _timestamp(value.capture_consent.granted_at),
        }
    return result
