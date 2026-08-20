"""MCP v0 adapter mapping strict wire DTOs to application service ports."""

from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from collections.abc import Callable, Mapping
from time import monotonic
from typing import Any, Protocol, cast

from pydantic import ValidationError

from .errors import PublicError, PublicErrorCode, map_service_error
from .observability import StructuredLogger, duration_bucket
from .schemas import (
    DEFAULT_TIMEOUT_MS,
    MAX_LIMIT,
    MAX_TIMEOUT_MS,
    PROTOCOL_VERSION,
    CapabilityResponse,
    ErrorBody,
    ErrorEnvelope,
    ForgetRequest,
    ForgetResponse,
    MemoryRecord,
    SearchRequest,
    SearchResponse,
    SearchResult,
    StrictModel,
    SuccessEnvelope,
    UpdateRequest,
    UpdateResponse,
    WriteRequest,
    WriteResponse,
)


class MemoryApplicationPort(Protocol):
    def write(self, payload: dict[str, Any]) -> Any: ...
    def search(self, payload: dict[str, Any]) -> Any: ...
    def update(self, payload: dict[str, Any]) -> Any: ...
    def forget(self, payload: dict[str, Any]) -> Any: ...


class RateLimiter(Protocol):
    def allow(self, tool: str) -> bool: ...


class FixedRateLimiter:
    def __init__(self, maximum: int | None = None) -> None:
        self.maximum = maximum
        self._calls = 0

    def allow(self, tool: str) -> bool:
        del tool
        if self.maximum is None:
            return True
        self._calls += 1
        return self._calls <= self.maximum


class MCPAdapter:
    """Transport-neutral adapter.

    ``local_mode=True`` is the only mode in which the caller-supplied
    ``owner_id`` is trusted. A hosted/authenticated composition must inject a
    trusted principal and reject these local payloads before this adapter.
    """

    TOOLS = ("memory.write", "memory.search", "memory.update", "memory.forget")

    def __init__(
        self,
        service: MemoryApplicationPort,
        *,
        local_mode: bool = True,
        transport: str = "stdio",
        logger: StructuredLogger | None = None,
        rate_limiter: RateLimiter | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if service.__class__.__name__ == "MemoryApplicationService":
            from .application_gateway import MemoryApplicationGateway

            service = MemoryApplicationGateway(cast(Any, service))
        self.service = service
        self.local_mode = local_mode
        self.transport = transport
        self.logger = logger or StructuredLogger(logging.getLogger("omp.mcp"))
        self.rate_limiter = rate_limiter or FixedRateLimiter()
        self.request_id_factory = request_id_factory or (lambda: "req_" + uuid.uuid4().hex)

    def capabilities(self, request_id: str | None = None) -> dict[str, Any]:
        return CapabilityResponse(
            request_id=request_id or self.request_id_factory(),
            transport="stdio",
            tools=list(self.TOOLS),
            limits={
                "max_content_length": 16_384,
                "max_query_length": 4_096,
                "max_limit": MAX_LIMIT,
                "max_timeout_ms": MAX_TIMEOUT_MS,
            },
            local_owner_payload=self.local_mode,
        ).model_dump(mode="json")

    def call_tool_sync(
        self, name: str, arguments: Mapping[str, Any] | None = None, request_id: str | None = None
    ) -> dict[str, Any]:
        return asyncio.run(self.call_tool(name, arguments, request_id=request_id))

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        rid = request_id or self.request_id_factory()
        started = monotonic()
        if name not in self.TOOLS:
            result = self._error(rid, PublicError(PublicErrorCode.VALIDATION, "unknown tool"))
            self._log(rid, name, result, started)
            return result
        if not self.rate_limiter.allow(name):
            result = self._error(
                rid,
                PublicError(PublicErrorCode.RATE_LIMITED, "rate limit exceeded", retryable=True),
            )
            self._log(rid, name, result, started)
            return result
        try:
            request = self._parse(name, arguments or {})
            if not self.local_mode:
                raise PublicError(PublicErrorCode.FORBIDDEN, "local owner payload is not accepted")
            timeout_ms = min(getattr(request, "timeout_ms", DEFAULT_TIMEOUT_MS), MAX_TIMEOUT_MS)
            data = await asyncio.wait_for(self._dispatch(name, request), timeout=timeout_ms / 1000)
            result = self._success(rid, data)
        except asyncio.CancelledError:
            raise
        except ValidationError:
            result = self._error(rid, PublicError(PublicErrorCode.VALIDATION, "invalid request"))
        except PublicError as error:
            result = self._error(rid, error)
        except TimeoutError:
            result = self._error(
                rid,
                PublicError(
                    PublicErrorCode.DEPENDENCY_UNAVAILABLE, "dependency unavailable", retryable=True
                ),
            )
        except BaseException as error:  # Boundary must never expose service details.
            mapped = map_service_error(error)
            result = self._error(rid, mapped)
        self._log(rid, name, result, started)
        return result

    def _parse(self, name: str, arguments: Mapping[str, Any]) -> StrictModel:
        models: dict[str, type[StrictModel]] = {
            "memory.write": WriteRequest,
            "memory.search": SearchRequest,
            "memory.update": UpdateRequest,
            "memory.forget": ForgetRequest,
        }
        return models[name].model_validate(dict(arguments))

    async def _dispatch(self, name: str, request: Any) -> dict[str, Any]:
        payload = request.model_dump(mode="json", exclude_none=True)
        method = getattr(self.service, name.rsplit(".", 1)[1], None)
        if method is None:
            method = getattr(self.service, f"{name.rsplit('.', 1)[1]}_memory", None)
        if method is None:
            raise RuntimeError("application service operation unavailable")
        response = method(payload)
        if inspect.isawaitable(response):
            response = await response
        if name == "memory.write":
            return WriteResponse.model_validate(response).model_dump(mode="json")
        if name == "memory.search":
            profile_version = None
            if isinstance(response, dict):
                items = response.get("items", response.get("memories", response))
                profile_version = response.get("profile_version")
            else:
                items = response
            normalized = [
                self._search_item(item, profile_version=profile_version)
                for item in cast(Any, items)
            ]
            return SearchResponse(memories=normalized, count=len(normalized)).model_dump(
                mode="json"
            )
        if name == "memory.update":
            return UpdateResponse.model_validate(response).model_dump(mode="json")
        return ForgetResponse.model_validate(response).model_dump(mode="json")

    def _search_item(self, item: Any, *, profile_version: str | None = None) -> SearchResult:
        reason: str | None = None
        item_profile_version = profile_version
        if isinstance(item, SearchResult):
            memory = item.memory
            score = item.score
            reason = item.reason_retrieved
            item_profile_version = item.retrieval_profile_version
        elif isinstance(item, Mapping):
            memory = item.get("memory", item)
            score = item.get("score", item.get("relevance", 0))
            reason = item.get("reason_retrieved")
            item_profile_version = item.get("profile_version", item_profile_version)
        else:
            memory = getattr(item, "memory", item)
            score = getattr(item, "score", getattr(item, "relevance", 0))
            reason = getattr(item, "reason_retrieved", None)
            item_profile_version = getattr(item, "profile_version", item_profile_version)
        record = MemoryRecord.model_validate(memory)
        bounded_score = max(0.0, min(1.0, float(score)))
        return SearchResult(
            memory=record,
            score=bounded_score,
            reason_retrieved=reason or self._reason(record.type, bounded_score),
            retrieval_profile_version=item_profile_version or "unknown",
        )

    @staticmethod
    def _reason(memory_type: str, score: float) -> str:
        band = "strong" if score >= 0.7 else "moderate" if score >= 0.35 else "weak"
        return (
            f"{band.capitalize()} baseline relevance match for a {memory_type} memory; "
            "above the configured threshold."
        )

    @staticmethod
    def _success(request_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return SuccessEnvelope(request_id=request_id, data=data).model_dump(mode="json")

    @staticmethod
    def _error(request_id: str, error: PublicError) -> dict[str, Any]:
        return ErrorEnvelope(
            request_id=request_id,
            error=ErrorBody(
                code=error.code.value, message=error.message, retryable=error.retryable
            ),
        ).model_dump(mode="json")

    def _log(self, request_id: str, tool: str, result: dict[str, Any], started: float) -> None:
        error_code = None if result.get("ok") else result.get("error", {}).get("code")
        result_count = None
        if result.get("ok") and isinstance(result.get("data"), dict):
            result_count = result["data"].get("count")
        self.logger.emit(
            event="mcp_request",
            request_id=request_id,
            tool=tool,
            status="ok" if result.get("ok") else "error",
            duration_ms=duration_bucket(started),
            protocol_version=PROTOCOL_VERSION,
            error_code=error_code,
            result_count=result_count,
        )
