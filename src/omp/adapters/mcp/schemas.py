"""Canonical, strict wire schemas for OMP MCP v0.

The schemas intentionally live at the protocol boundary. They are not the
domain model and must be mapped to application commands by the adapter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROTOCOL_VERSION = "omp.mcp.v0"
MCP_PROTOCOL_VERSION = "2025-11-25"
MAX_CONTENT_LENGTH = 16_384
MAX_QUERY_LENGTH = 4_096
MAX_LIMIT = 50
DEFAULT_TIMEOUT_MS = 2_500
MAX_TIMEOUT_MS = 5_000


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


MemoryType = Literal[
    "fact",
    "preference",
    "decision",
    "insight",
    "hypothesis",
    "lesson",
    "goal",
    "project_context",
    "concept",
    "relationship",
    "open_question",
]
MemoryState = Literal["active", "superseded", "contradicted", "archived"]


class Provenance(StrictModel):
    source_type: Literal["conversation", "user", "agent", "import", "system", "unknown", "other"]
    captured_at: str = Field(min_length=1, max_length=80)
    source_id: str | None = Field(default=None, max_length=256)
    source_model: str | None = Field(default=None, max_length=128)
    evidence: str | None = Field(default=None, max_length=2_000)

    @field_validator("captured_at")
    @classmethod
    def valid_timestamp(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("captured_at must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


class MemoryPatch(StrictModel):
    content: str | None = Field(default=None, min_length=1, max_length=MAX_CONTENT_LENGTH)
    type: MemoryType | None = None
    space: str | None = Field(default=None, min_length=1, max_length=128)
    importance: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    state: MemoryState | None = None
    provenance: Provenance | None = None

    @model_validator(mode="after")
    def has_change(self) -> MemoryPatch:
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("patch must contain at least one change")
        return self

    @field_validator("content")
    @classmethod
    def non_blank_content(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("content must not be blank")
        return value


class WriteRequest(StrictModel):
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)
    type: MemoryType
    owner_id: str = Field(min_length=1, max_length=128)
    space: str | None = Field(default=None, min_length=1, max_length=128)
    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    provenance: Provenance
    idempotency_key: str = Field(min_length=1, max_length=128)
    timeout_ms: int = Field(default=DEFAULT_TIMEOUT_MS, ge=1, le=MAX_TIMEOUT_MS)

    @field_validator("content")
    @classmethod
    def non_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class SearchRequest(StrictModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    owner_id: str = Field(min_length=1, max_length=128)
    space: str | None = Field(default=None, min_length=1, max_length=128)
    type: MemoryType | None = None
    state: MemoryState | None = None
    limit: int = Field(default=10, ge=1, le=MAX_LIMIT)
    min_relevance: float = Field(default=0.78, ge=0, le=1)
    timeout_ms: int = Field(default=DEFAULT_TIMEOUT_MS, ge=1, le=MAX_TIMEOUT_MS)

    @field_validator("query")
    @classmethod
    def non_blank_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value


class UpdateRequest(StrictModel):
    id: str = Field(min_length=1, max_length=128)
    owner_id: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=1)
    patch: MemoryPatch
    provenance: Provenance | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)
    timeout_ms: int = Field(default=DEFAULT_TIMEOUT_MS, ge=1, le=MAX_TIMEOUT_MS)


class ForgetRequest(StrictModel):
    id: str = Field(min_length=1, max_length=128)
    owner_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=256)
    timeout_ms: int = Field(default=DEFAULT_TIMEOUT_MS, ge=1, le=MAX_TIMEOUT_MS)


class MemoryRecord(StrictModel):
    id: str = Field(min_length=1, max_length=128)
    owner_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)
    type: MemoryType
    space: str | None = Field(default=None, max_length=128)
    importance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    state: MemoryState
    version: int = Field(ge=1)
    created_at: str = Field(min_length=1, max_length=80)
    updated_at: str = Field(min_length=1, max_length=80)
    occurred_at: str | None = Field(default=None, max_length=80)
    provenance: Provenance


class SearchResult(StrictModel):
    memory: MemoryRecord
    score: float = Field(ge=0, le=1)
    reason_retrieved: str = Field(min_length=1, max_length=256)
    retrieval_profile_version: str = Field(min_length=1, max_length=64)


class WriteResponse(StrictModel):
    memory: MemoryRecord
    status: Literal["created", "already_exists"]


class SearchResponse(StrictModel):
    memories: list[SearchResult]
    count: int = Field(ge=0, le=MAX_LIMIT)


class UpdateResponse(StrictModel):
    memory: MemoryRecord
    status: Literal["updated"]


class ForgetResponse(StrictModel):
    status: Literal["forgotten", "already_absent"]


class SuccessEnvelope(StrictModel):
    protocol_version: Literal["omp.mcp.v0"] = "omp.mcp.v0"
    request_id: str = Field(min_length=1, max_length=128)
    ok: Literal[True] = True
    data: dict[str, Any]


class ErrorBody(StrictModel):
    code: Literal[
        "validation_error",
        "not_found",
        "version_conflict",
        "forbidden",
        "rate_limited",
        "dependency_unavailable",
        "internal_error",
    ]
    message: str = Field(min_length=1, max_length=256)
    retryable: bool = False


class ErrorEnvelope(StrictModel):
    protocol_version: Literal["omp.mcp.v0"] = "omp.mcp.v0"
    request_id: str = Field(min_length=1, max_length=128)
    ok: Literal[False] = False
    error: ErrorBody


class CapabilityResponse(StrictModel):
    protocol_version: Literal["omp.mcp.v0"] = "omp.mcp.v0"
    request_id: str = Field(min_length=1, max_length=128)
    mcp_protocol_version: str = MCP_PROTOCOL_VERSION
    server_name: str = "open-memory-protocol"
    server_version: str = "0.1.0a1"
    transport: Literal["stdio"]
    tools: list[str]
    limits: dict[str, int]
    local_owner_payload: bool
