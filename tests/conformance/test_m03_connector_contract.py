from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from examples.connectors import (
    CHATGPT_SIM,
    CLAUDE_SIM,
    CONSENT,
    PROVENANCE,
    READER_SIM,
    TENANT_B_SIM,
    ConnectorContractError,
    SyntheticLocalAdapter,
)

ROOT = Path(__file__).parents[2]
CONTRACT = ROOT / "docs/contracts/mcp/v1"
EXPECTED_SCOPES = {
    "consent:grant",
    "memory:read",
    "memory:write",
    "memory:delete",
    "connection:revoke",
}


def _assert_code(code: str, action: Callable[[], object]) -> None:
    with pytest.raises(ConnectorContractError) as error:
        action()
    assert error.value.code == code


def test_v1_contract_is_machine_readable_and_labels_compatibility_boundary() -> None:
    capabilities = json.loads((CONTRACT / "capabilities.json").read_text())
    requests = json.loads((CONTRACT / "requests.json").read_text())
    events = json.loads((CONTRACT / "events.json").read_text())

    assert capabilities["contract_version"] == "omp.mcp.v1.connector-preflight"
    assert set(capabilities["scope_vocabulary"]) == EXPECTED_SCOPES
    assert {item["operation"] for item in capabilities["capabilities"]} == {
        "consent.grant",
        "memory.capture",
        "memory.recall",
        "memory.update",
        "memory.forget",
        "connection.revoke",
    }
    assert requests["$defs"]["CaptureRequest"]["required"] == [
        "content",
        "consent_id",
        "provenance",
        "idempotency_key",
    ]
    assert events["$defs"]["ConnectionRevoked"]["properties"]["event_type"] == {
        "const": "connection.revoked"
    }
    labels = capabilities["compatibility"]
    assert labels["tested"]
    assert labels["not-tested"]
    assert any("OAuth" in label for label in labels["not-tested"])
    assert any("real ChatGPT" in label for label in labels["not-tested"])


def test_scope_matrix_denies_missing_scopes_and_revocation_is_fail_closed() -> None:
    adapter = SyntheticLocalAdapter((CHATGPT_SIM, CLAUDE_SIM, READER_SIM, TENANT_B_SIM))

    _assert_code("scope_denied", lambda: adapter.grant_consent("reader-sim", CONSENT))
    _assert_code(
        "scope_denied",
        lambda: adapter.update(
            "reader-sim",
            memory_id="memory-missing",
            content="not allowed",
            idempotency_key="idem-reader-update",
        ),
    )
    _assert_code(
        "scope_denied",
        lambda: adapter.forget(
            "reader-sim", memory_id="memory-missing", idempotency_key="idem-reader-forget"
        ),
    )
    _assert_code(
        "scope_denied",
        lambda: adapter.revoke("claude-sim", target_connection_id=CHATGPT_SIM.connection_id),
    )


def test_cross_client_journey_preserves_provenance_reason_idempotency_and_revoke() -> None:
    adapter = SyntheticLocalAdapter((CHATGPT_SIM, CLAUDE_SIM, READER_SIM, TENANT_B_SIM))
    content = "Teams should optimize outcomes, not merely the metric."

    _assert_code(
        "consent_required",
        lambda: adapter.capture(
            "chatgpt-sim",
            content=content,
            consent_id=CONSENT.consent_id,
            provenance=PROVENANCE,
            idempotency_key="idem-capture-001",
        ),
    )
    assert adapter.grant_consent("chatgpt-sim", CONSENT) == CONSENT
    _assert_code(
        "consent_required",
        lambda: adapter.capture(
            "claude-sim",
            content=content,
            consent_id=CONSENT.consent_id,
            provenance=PROVENANCE,
            idempotency_key="idem-claude-capture-before-consent",
        ),
    )
    captured = adapter.capture(
        "chatgpt-sim",
        content=content,
        consent_id=CONSENT.consent_id,
        provenance=PROVENANCE,
        idempotency_key="idem-capture-001",
    )
    assert captured.provenance == PROVENANCE
    assert captured.version == 1

    assert adapter.grant_consent("claude-sim", CONSENT) == CONSENT
    recalled = adapter.recall("claude-sim", query="outcomes")
    assert len(recalled) == 1
    assert recalled[0]["memory_id"] == captured.memory_id
    assert recalled[0]["provenance"] == PROVENANCE
    assert recalled[0]["reason_retrieved"] == "explicit_connector_semantic_match"
    assert adapter.recall("tenant-b-sim", query="outcomes") == ()

    updated = adapter.update(
        "claude-sim",
        memory_id=captured.memory_id,
        content="Teams should optimize durable outcomes, not merely the metric.",
        idempotency_key="idem-update-001",
    )
    replayed_update = adapter.update(
        "claude-sim",
        memory_id=captured.memory_id,
        content=updated.content,
        idempotency_key="idem-update-001",
    )
    assert replayed_update == updated
    assert replayed_update.version == 2
    assert adapter.recall("claude-sim", query="durable outcomes")[0]["content"] == updated.content

    forgotten = adapter.forget(
        "claude-sim", memory_id=captured.memory_id, idempotency_key="idem-forget-001"
    )
    assert forgotten == {"memory_id": captured.memory_id, "status": "forgotten"}
    assert adapter.forget(
        "claude-sim", memory_id=captured.memory_id, idempotency_key="idem-forget-001"
    ) == forgotten
    assert adapter.forget(
        "claude-sim", memory_id=captured.memory_id, idempotency_key="idem-forget-002"
    ) == {"memory_id": captured.memory_id, "status": "already_absent"}

    captured_again = adapter.capture(
        "chatgpt-sim",
        content=content,
        consent_id=CONSENT.consent_id,
        provenance=PROVENANCE,
        idempotency_key="idem-capture-002",
    )
    event = adapter.revoke("chatgpt-sim", target_connection_id=CHATGPT_SIM.connection_id)
    assert event == {
        "event_id": "event-connection-revoked-001",
        "event_type": "connection.revoked",
        "connection_id": "conn-chatgpt-sim",
        "revoked_at": "2026-08-24T12:01:00Z",
        "reason": "user_requested_revocation",
    }
    assert adapter.events == (event,)
    _assert_code("connection_revoked", lambda: adapter.recall("chatgpt-sim", query="outcomes"))
    _assert_code(
        "connection_revoked",
        lambda: adapter.capture(
            "chatgpt-sim",
            content="new capture",
            consent_id=CONSENT.consent_id,
            provenance=PROVENANCE,
            idempotency_key="idem-capture-003",
        ),
    )
    assert adapter.recall("claude-sim", query="outcomes") == (
        {
            "memory_id": captured_again.memory_id,
            "content": content,
            "provenance": PROVENANCE,
            "reason_retrieved": "explicit_connector_semantic_match",
        },
    )
