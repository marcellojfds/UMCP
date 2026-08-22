from __future__ import annotations

import pytest
from tests.fixtures.m1_http import (
    AUTHORITY_FIELDS,
    M1_TOOL_NAMES,
    M1HTTPClient,
    required_fields,
    synthetic_principals,
    tool_spec,
)

EXPECTED_REQUIRED_FIELDS = {
    "memory.capture": {"content", "type", "space", "provenance", "consent", "idempotency_key"},
    "memory.inbox.list": set(),
    "memory.inbox.confirm": {"id", "expected_version", "idempotency_key"},
    "memory.inbox.discard": {"id", "expected_version", "idempotency_key"},
    "memory.pin": {"id", "expected_version", "pinned", "idempotency_key"},
    "memory.recall": {"query", "context_space"},
    "memory.update": {"id", "expected_version", "patch", "idempotency_key"},
    "memory.forget": {"id", "idempotency_key"},
}


@pytest.mark.asyncio
async def test_m1_http_tools_are_discoverable_with_strict_authority_boundary() -> None:
    """Read only the public HTTP/MCP surface; no fixture store is involved."""
    principal = synthetic_principals()["chatgpt-sim"]
    async with M1HTTPClient(principal) as client:
        tools = await client.list_tools()

    by_name = {tool_spec(tool)[0]: tool for tool in tools}
    assert set(by_name) == M1_TOOL_NAMES
    for name in M1_TOOL_NAMES:
        _, schema, _ = tool_spec(by_name[name])
        assert schema.get("additionalProperties") is False
        assert not AUTHORITY_FIELDS.intersection(schema.get("properties", {}))
        assert required_fields(schema) == EXPECTED_REQUIRED_FIELDS[name]


@pytest.mark.asyncio
async def test_m1_http_tool_annotations_are_safe_and_deterministic() -> None:
    principal = synthetic_principals()["claude-sim"]
    async with M1HTTPClient(principal) as client:
        tools = await client.list_tools()

    by_name = {tool_spec(tool)[0]: tool for tool in tools}
    for name in ("memory.inbox.list", "memory.recall"):
        _, _, annotations = tool_spec(by_name[name])
        assert annotations is not None
        assert annotations.readOnlyHint is True
        assert annotations.destructiveHint is False
    for name in ("memory.capture", "memory.inbox.confirm", "memory.pin", "memory.update"):
        _, _, annotations = tool_spec(by_name[name])
        assert annotations is not None
        assert annotations.readOnlyHint is False
        assert annotations.destructiveHint is False
        assert annotations.idempotentHint is True
    _, _, annotations = tool_spec(by_name["memory.inbox.discard"])
    assert annotations is not None
    assert annotations.readOnlyHint is False
    assert annotations.destructiveHint is True
    assert annotations.idempotentHint is True
    _, _, annotations = tool_spec(by_name["memory.forget"])
    assert annotations is not None
    assert annotations.readOnlyHint is False
    assert annotations.destructiveHint is True
    assert annotations.idempotentHint is True


@pytest.mark.asyncio
async def test_m1_http_rejects_forged_authority_before_persistence() -> None:
    principal = synthetic_principals()["chatgpt-sim"]
    async with M1HTTPClient(principal) as client:
        code = await client.expect_error(
            "memory.capture",
            {
                "content": "synthetic authority-negative canary",
                "type": "lesson",
                "space": "MBA",
                "provenance": {
                    "source_type": "conversation",
                    "captured_at": "2026-08-22T12:00:00Z",
                },
                "consent": {
                    "mode": "assisted",
                    "consent_id": "consent-contract-negative",
                    "reason_code": "user_requested_memory",
                    "granted_at": "2026-08-22T12:00:00Z",
                },
                "idempotency_key": "m1-contract-authority-negative",
                "owner_id": "forged-owner",
            },
            step="authority-negative",
        )
    assert code == "validation_error"
