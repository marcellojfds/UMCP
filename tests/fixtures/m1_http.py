"""Black-box M1 HTTP fixture and acceptance journey.

This module is verification-owned evidence.  It deliberately knows only the
public M1 MCP tools plus two local-development HTTP control hooks for the
connection revocation and restore/import steps, which are not MCP tools in the
frozen contract.  It never imports the product domain, application, or store.
"""

from __future__ import annotations

import json
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

M1_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "memory.capture",
        "memory.inbox.list",
        "memory.inbox.confirm",
        "memory.inbox.discard",
        "memory.pin",
        "memory.recall",
        "memory.update",
        "memory.forget",
    }
)
AUTHORITY_FIELDS: Final[frozenset[str]] = frozenset(
    {"tenant_id", "owner_id", "connection_id", "scopes"}
)
M1_RECALL_REASON: Final[str] = "explicit_cross_space_semantic_match"
CAPTURED_AT: Final[str] = "2026-08-22T12:00:00Z"
CANONICAL_CONTENT: Final[str] = (
    "Poorly designed incentives make teams optimize the metric, not the outcome."
)
RECALL_QUERY: Final[str] = (
    "Why did the work team increase closed tickets while customer satisfaction fell?"
)


class M1HarnessError(RuntimeError):
    """Safe, non-sensitive error reported by the harness."""

    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


class M1HarnessConfigurationError(M1HarnessError):
    """The product-under-test endpoint lacks a required local test hook."""


class M1ToolError(M1HarnessError):
    """A public MCP tool returned an error code."""

    def __init__(self, step: str, code: str) -> None:
        super().__init__(step, f"tool error code={code}")
        self.code = code


@dataclass(frozen=True, slots=True)
class SyntheticPrincipal:
    name: str
    tenant: str
    user: str
    connection_id: str
    token: str


@dataclass(frozen=True, slots=True)
class ScenarioReport:
    scenario_id: str
    counts: dict[str, int]


def _env_token(name: str, fallback: str) -> str:
    value = os.getenv(name, fallback).strip()
    if not value:
        raise M1HarnessConfigurationError("configuration", f"empty token variable {name}")
    return value


def synthetic_principals() -> dict[str, SyntheticPrincipal]:
    """Return deterministic fixture identities; tokens are supplied by the local verifier."""
    return {
        "chatgpt-sim": SyntheticPrincipal(
            "chatgpt-sim",
            "tenant-a",
            "user-a",
            "conn-chatgpt-sim",
            _env_token("M1_TOKEN_CHATGPT_SIM", "m1-fixture-chatgpt-sim"),
        ),
        "claude-sim": SyntheticPrincipal(
            "claude-sim",
            "tenant-a",
            "user-a",
            "conn-claude-sim",
            _env_token("M1_TOKEN_CLAUDE_SIM", "m1-fixture-claude-sim"),
        ),
        "chatgpt-sim-b": SyntheticPrincipal(
            "chatgpt-sim-b",
            "tenant-b",
            "user-b",
            "conn-chatgpt-sim-b",
            _env_token("M1_TOKEN_CHATGPT_SIM_B", "m1-fixture-chatgpt-sim-b"),
        ),
    }


def m1_http_url() -> str:
    value = os.getenv("M1_HTTP_URL", "http://127.0.0.1:8000/mcp").strip()
    if not value.startswith(("http://", "https://")):
        raise M1HarnessConfigurationError("configuration", "M1_HTTP_URL must be an HTTP URL")
    return value


def _json_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    for block in getattr(result, "content", ()):
        if getattr(block, "type", None) != "text":
            continue
        try:
            payload = json.loads(str(getattr(block, "text", "")))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    raise M1HarnessError("mcp", "response was not a JSON object")


def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove only a transport envelope; public M1 fields stay untouched."""
    data = payload.get("data")
    if payload.get("ok") is True and isinstance(data, dict):
        return data
    return payload


def _error_code(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if not isinstance(error, dict):
        data = payload.get("data")
        error = data.get("error") if isinstance(data, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    return str(code) if isinstance(code, str) and code else "remote_error"


class M1HTTPClient:
    """One authenticated MCP Streamable HTTP session for one fixture principal."""

    def __init__(self, principal: SyntheticPrincipal, *, url: str | None = None) -> None:
        self.principal = principal
        self.url = url or m1_http_url()
        self.session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    async def __aenter__(self) -> M1HTTPClient:
        stack = AsyncExitStack()
        await stack.__aenter__()
        self._stack = stack
        http = await stack.enter_async_context(
            httpx.AsyncClient(
                headers={
                    "authorization": f"Bearer {self.principal.token}",
                    "accept": "application/json, text/event-stream",
                },
                timeout=float(os.getenv("M1_HTTP_TIMEOUT_SECONDS", "15")),
            )
        )
        try:
            await http.get(self.url)
        except httpx.HTTPError:
            await stack.aclose()
            self._stack = None
            raise M1HarnessError("initialize", "M1 HTTP endpoint is unavailable") from None
        try:
            read_stream, write_stream, _ = await stack.enter_async_context(
                streamable_http_client(self.url, http_client=http)
            )
            self.session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await self.session.initialize()
        except Exception:
            await stack.aclose()
            self._stack = None
            raise M1HarnessError(
                "initialize", "M1 HTTP MCP session could not be initialized"
            ) from None
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self.session = None

    async def list_tools(self) -> list[Any]:
        if self.session is None:
            raise M1HarnessError("tools/list", "MCP session is not open")
        try:
            return list((await self.session.list_tools()).tools)
        except Exception:
            raise M1HarnessError("tools/list", "MCP tools could not be listed") from None

    async def call(self, name: str, arguments: dict[str, Any], *, step: str) -> dict[str, Any]:
        if self.session is None:
            raise M1HarnessError(step, "MCP session is not open")
        try:
            result = await self.session.call_tool(name, arguments)
        except Exception:
            raise M1HarnessError(step, "MCP tool call failed") from None
        payload = _json_payload(result)
        if bool(getattr(result, "isError", False)) or "error" in payload:
            raise M1ToolError(step, _error_code(payload))
        return _unwrap(payload)

    async def expect_error(self, name: str, arguments: dict[str, Any], *, step: str) -> str:
        try:
            await self.call(name, arguments, step=step)
        except M1ToolError as error:
            return error.code
        raise M1HarnessError(step, "expected a public MCP error")


def _require(condition: bool, step: str, detail: str) -> None:
    if not condition:
        raise M1HarnessError(step, detail)


def _require_keys(value: Any, keys: tuple[str, ...], step: str) -> None:
    _require(isinstance(value, dict), step, "object missing")
    _require(all(key in value for key in keys), step, "required public fields missing")


def _memory_from(payload: dict[str, Any], step: str) -> dict[str, Any]:
    memory = payload.get("memory")
    _require(isinstance(memory, dict), step, "memory object missing")
    return memory


def _provenance_is_canonical(memory: dict[str, Any], step: str) -> None:
    provenance = memory.get("provenance")
    _require(isinstance(provenance, dict), step, "provenance missing")
    expected = {
        "source_client": "chatgpt-sim",
        "source_type": "conversation",
        "source_connection_id": "conn-chatgpt-sim",
        "conversation_id": "conv-opaque-001",
        "message_id": "msg-opaque-007",
        "source_model": "model-opaque",
        "captured_at": CAPTURED_AT,
        "evidence": ["user-selected-excerpt-1"],
    }
    _require(
        all(provenance.get(key) == value for key, value in expected.items()),
        step,
        "provenance mismatch",
    )


def _consent_is_canonical(memory: dict[str, Any], step: str) -> None:
    consent = memory.get("capture_consent")
    _require(isinstance(consent, dict), step, "capture consent missing")
    expected = {
        "mode": "assisted",
        "consent_id": "consent-opaque-001",
        "reason_code": "user_requested_memory",
        "policy_version": "m1-local-1",
        "granted_at": CAPTURED_AT,
    }
    _require(
        all(consent.get(key) == value for key, value in expected.items()),
        step,
        "consent mismatch",
    )


async def _post_control(
    url: str | None,
    *,
    step: str,
    principal: SyntheticPrincipal,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not url:
        raise M1HarnessConfigurationError(
            step,
            "local HTTP control hook is required; set M1_REVOKE_URL or M1_RESTORE_URL",
        )
    try:
        async with httpx.AsyncClient(
            headers={
                "authorization": f"Bearer {principal.token}",
                "accept": "application/json",
            },
            timeout=float(os.getenv("M1_HTTP_TIMEOUT_SECONDS", "15")),
        ) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError:
        raise M1HarnessError(step, "local HTTP control hook failed") from None
    if response.status_code < 200 or response.status_code >= 300:
        raise M1HarnessError(step, "local HTTP control hook rejected the request")
    try:
        result = response.json()
    except (ValueError, json.JSONDecodeError):
        raise M1HarnessError(step, "local HTTP control hook returned invalid JSON") from None
    _require(isinstance(result, dict), step, "local HTTP control response was not an object")
    return result


def _export_package(memory: dict[str, Any]) -> dict[str, Any]:
    """Build the synthetic pre-forget package without persisting it locally."""
    exported_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "format": "omp.export.v0",
        "exported_at": exported_at,
        "includes_embeddings": False,
        "memories": [memory],
    }


async def revoke_chatgpt(principal: SyntheticPrincipal) -> None:
    await _post_control(
        os.getenv("M1_REVOKE_URL", "").strip() or None,
        step="revoke",
        principal=principal,
        payload={"connection_id": principal.connection_id, "client": principal.name},
    )


async def restore_package(principal: SyntheticPrincipal, memory: dict[str, Any]) -> dict[str, Any]:
    return await _post_control(
        os.getenv("M1_RESTORE_URL", "").strip() or None,
        step="restore",
        principal=principal,
        payload=_export_package(memory),
    )


async def run_m1_acceptance(*, scenario_id: str | None = None) -> ScenarioReport:
    """Run the ten-step frozen acceptance journey through the M1 HTTP boundary."""
    principals = synthetic_principals()
    chatgpt = principals["chatgpt-sim"]
    claude = principals["claude-sim"]
    tenant_b = principals["chatgpt-sim-b"]
    run_id = scenario_id or f"m1-portable-memory-{os.urandom(6).hex()}"

    def key(label: str) -> str:
        return f"{run_id}-{label}"

    counts = {"candidate": 0, "recall": 0, "tenant_b": 0, "forgotten": 0, "restored": 0}

    async with M1HTTPClient(chatgpt) as chat_client:
        capture = await chat_client.call(
            "memory.capture",
            {
                "content": CANONICAL_CONTENT,
                "type": "lesson",
                "space": "MBA",
                "provenance": {
                    "source_type": "conversation",
                    "source_client": "chatgpt-sim",
                    "source_connection_id": "conn-chatgpt-sim",
                    "conversation_id": "conv-opaque-001",
                    "message_id": "msg-opaque-007",
                    "source_model": "model-opaque",
                    "captured_at": CAPTURED_AT,
                    "evidence": ["user-selected-excerpt-1"],
                },
                "consent": {
                    "mode": "assisted",
                    "consent_id": "consent-opaque-001",
                    "reason_code": "user_requested_memory",
                    "policy_version": "m1-local-1",
                    "granted_at": CAPTURED_AT,
                },
                "idempotency_key": key("capture"),
            },
            step="capture",
        )
        _require(capture.get("status") == "created", "capture", "status is not created")
        captured_memory = _memory_from(capture, "capture")
        _require(captured_memory.get("state") == "candidate", "capture", "state is not candidate")
        _require(captured_memory.get("type") == "lesson", "capture", "type is not lesson")
        _require(captured_memory.get("space") == "MBA", "capture", "space is not MBA")
        _require(captured_memory.get("content") == CANONICAL_CONTENT, "capture", "content mismatch")
        _provenance_is_canonical(captured_memory, "capture")
        _consent_is_canonical(captured_memory, "capture")
        memory_id = captured_memory.get("id")
        version = captured_memory.get("version")
        _require(isinstance(memory_id, str) and bool(memory_id), "capture", "memory id missing")
        _require(isinstance(version, int) and version > 0, "capture", "memory version missing")
        counts["candidate"] = 1

        default_recall = await chat_client.call(
            "memory.recall",
            {"query": RECALL_QUERY, "context_space": "MBA"},
            step="candidate-recall",
        )
        _require(default_recall.get("count") == 0, "candidate-recall", "candidate was recalled")

        inbox = await chat_client.call(
            "memory.inbox.list", {"space": "MBA", "limit": 10}, step="inbox-list"
        )
        candidates = inbox.get("candidates")
        _require(
            isinstance(candidates, list) and len(candidates) == 1,
            "inbox-list",
            "candidate count mismatch",
        )
        _require(candidates[0].get("id") == memory_id, "inbox-list", "unexpected candidate")

        confirm = await chat_client.call(
            "memory.inbox.confirm",
            {
                "id": memory_id,
                "expected_version": version,
                "idempotency_key": key("confirm"),
            },
            step="inbox-confirm",
        )
        confirmed = _memory_from(confirm, "inbox-confirm")
        _require(confirm.get("status") == "confirmed", "inbox-confirm", "status is not confirmed")
        _require(confirmed.get("state") == "confirmed", "inbox-confirm", "state is not confirmed")
        _require(
            confirmed.get("version") == version + 1,
            "inbox-confirm",
            "version did not increment",
        )
        _provenance_is_canonical(confirmed, "inbox-confirm")
        _consent_is_canonical(confirmed, "inbox-confirm")
        pre_forget = confirmed

        invalid_code = await chat_client.expect_error(
            "memory.capture",
            {
                "content": CANONICAL_CONTENT,
                "type": "lesson",
                "space": "MBA",
                "provenance": {"source_type": "conversation", "captured_at": CAPTURED_AT},
                "consent": {
                    "mode": "assisted",
                    "consent_id": "consent-invalid-001",
                    "reason_code": "user_requested_memory",
                    "granted_at": CAPTURED_AT,
                },
                "idempotency_key": key("authority-negative"),
                "tenant_id": "tenant-b-forged",
            },
            step="authority-negative",
        )
        _require(
            invalid_code == "validation_error",
            "authority-negative",
            "authority field was accepted",
        )

    async with M1HTTPClient(tenant_b) as tenant_b_client:
        tenant_b_inbox = await tenant_b_client.call(
            "memory.inbox.list", {"space": "MBA", "limit": 10}, step="tenant-b-inbox"
        )
        _require(
            tenant_b_inbox.get("candidates") == [],
            "tenant-b-inbox",
            "tenant B saw a candidate",
        )
        tenant_b_recall = await tenant_b_client.call(
            "memory.recall",
            {"query": RECALL_QUERY, "context_space": "Work", "include_spaces": ["MBA"]},
            step="tenant-b-recall",
        )
        _require(
            tenant_b_recall.get("count") == 0,
            "tenant-b-recall",
            "tenant B received a result",
        )
        _require(
            tenant_b_recall.get("memories") == [],
            "tenant-b-recall",
            "tenant B result list was non-empty",
        )

    async with M1HTTPClient(claude) as claude_client:
        recall_args = {
            "query": RECALL_QUERY,
            "context_space": "Work",
            "include_spaces": ["MBA"],
            "limit": 10,
        }
        recall = await claude_client.call("memory.recall", recall_args, step="claude-recall")
        memories = recall.get("memories")
        _require(
            isinstance(memories, list) and len(memories) == 1,
            "claude-recall",
            "recall count mismatch",
        )
        record = memories[0]
        _require(record.get("type") == "lesson", "claude-recall", "recall type mismatch")
        _require(record.get("space") == "MBA", "claude-recall", "recall space mismatch")
        _require(
            record.get("reason_retrieved") == M1_RECALL_REASON,
            "claude-recall",
            "recall reason mismatch",
        )
        _require(
            record.get("content") == CANONICAL_CONTENT,
            "claude-recall",
            "recall content mismatch",
        )
        provenance = record.get("provenance")
        _require(isinstance(provenance, dict), "claude-recall", "recall provenance missing")
        _require(
            provenance.get("source_client") == "chatgpt-sim",
            "claude-recall",
            "source client mismatch",
        )
        _require(
            provenance.get("source_type") == "conversation",
            "claude-recall",
            "source type mismatch",
        )
        _require(
            provenance.get("captured_at") == CAPTURED_AT,
            "claude-recall",
            "captured_at mismatch",
        )
        _require(
            provenance.get("conversation_id") == "conv-opaque-001",
            "claude-recall",
            "conversation id missing",
        )
        _require(
            provenance.get("message_id") == "msg-opaque-007",
            "claude-recall",
            "message id missing",
        )
        counts["recall"] = 1

        await revoke_chatgpt(claude)
        async with M1HTTPClient(chatgpt) as revoked_chatgpt:
            revoked_code = await revoked_chatgpt.expect_error(
                "memory.capture",
                {
                    "content": "A second synthetic lesson that must not persist.",
                    "type": "lesson",
                    "space": "MBA",
                    "provenance": {
                        "source_type": "conversation",
                        "source_client": "chatgpt-sim",
                        "captured_at": CAPTURED_AT,
                    },
                    "consent": {
                        "mode": "assisted",
                        "consent_id": "consent-opaque-002",
                        "reason_code": "user_requested_memory",
                        "granted_at": CAPTURED_AT,
                    },
                    "idempotency_key": key("revoked-capture"),
                },
                step="revoked-capture",
            )
            _require(
                revoked_code in {"connection_revoked", "scope_denied"},
                "revoked-capture",
                "revoked connection was not denied safely",
            )

        after_revoke = await claude_client.call(
            "memory.recall", recall_args, step="claude-after-revoke"
        )
        _require(
            after_revoke.get("count") == 1,
            "claude-after-revoke",
            "Claude was revoked with ChatGPT",
        )

        forgotten = await claude_client.call(
            "memory.forget",
            {"id": memory_id, "idempotency_key": key("forget")},
            step="forget",
        )
        _require(forgotten.get("status") == "forgotten", "forget", "status is not forgotten")
        counts["forgotten"] = 1
        repeated = await claude_client.call(
            "memory.forget",
            {"id": memory_id, "idempotency_key": key("forget")},
            step="forget-replay",
        )
        _require(
            repeated.get("status") == "already_absent",
            "forget-replay",
            "same-key replay mutated again",
        )
        different = await claude_client.call(
            "memory.forget",
            {"id": memory_id, "idempotency_key": key("forget-different")},
            step="forget-repeat",
        )
        _require(
            different.get("status") == "already_absent",
            "forget-repeat",
            "different-key forget mutated again",
        )
        restored = await restore_package(claude, pre_forget)
        restore_status = restored.get("status") or restored.get("result")
        _require(
            restore_status in {"restore_blocked_by_tombstone", "skipped-tombstone"},
            "restore",
            "restore did not report tombstone blocking",
        )
        counts["restored"] = 0
        after_restore = await claude_client.call(
            "memory.recall", recall_args, step="post-restore-recall"
        )
        _require(
            after_restore.get("count") == 0,
            "post-restore-recall",
            "forgotten memory was resurrected",
        )

    return ScenarioReport(run_id, counts)


def tool_spec(tool: Any) -> tuple[str, dict[str, Any], Any]:
    name = str(getattr(tool, "name", ""))
    schema = getattr(tool, "inputSchema", None)
    annotations = getattr(tool, "annotations", None)
    return name, schema if isinstance(schema, dict) else {}, annotations


def required_fields(schema: dict[str, Any]) -> set[str]:
    value = schema.get("required", [])
    return {str(item) for item in value} if isinstance(value, list) else set()
