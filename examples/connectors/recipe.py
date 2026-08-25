"""Runnable MCP connector contract v1 recipe over synthetic fixtures only.

This module is deliberately a local adapter example, not a client integration
or an authentication implementation.  Run it from the repository root with::

    python -m examples.connectors.recipe
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Final

from .fixtures import (
    CHATGPT_SIM,
    CLAUDE_SIM,
    CONSENT,
    PROVENANCE,
    TENANT_B_SIM,
    ConnectorFixture,
    Scope,
)
from .local_adapter import ConnectorContractError, SyntheticLocalAdapter

V1_CONTRACT_VERSION: Final = "omp.mcp.v1.connector-preflight"
CONTENT: Final = "Teams should optimize outcomes, not merely the metric."
UPDATED_CONTENT: Final = "Teams should optimize durable outcomes, not merely the metric."

REQUIRED_SCOPES_BY_OPERATION: Final[dict[str, frozenset[Scope]]] = {
    "consent.grant": frozenset({"consent:grant"}),
    "memory.capture": frozenset({"memory:write"}),
    "memory.recall": frozenset({"memory:read"}),
    "memory.update": frozenset({"memory:write"}),
    "memory.forget": frozenset({"memory:delete"}),
    "connection.revoke": frozenset({"connection:revoke"}),
}

SOURCE_OPERATIONS: Final = ("consent.grant", "memory.capture", "connection.revoke")
COLLABORATOR_OPERATIONS: Final = (
    "consent.grant",
    "memory.recall",
    "memory.update",
    "memory.forget",
)
TENANT_B_OPERATIONS: Final = ("memory.recall",)


@dataclass(frozen=True, slots=True)
class RecipeResult:
    """Stable, redacted summary emitted by the runnable recipe."""

    contract_version: str
    source_scopes: tuple[str, ...]
    collaborator_scopes: tuple[str, ...]
    tenant_b_scopes: tuple[str, ...]
    captured_memory_id: str
    recalled_memory_ids: tuple[str, ...]
    recalled_reason: str
    provenance_source_connection_id: str
    updated_version: int
    forgotten_status: str
    tenant_b_recall_count: int
    revoked_connection_id: str
    surviving_client_recall_ids: tuple[str, ...]


def _minimal_fixture(fixture: ConnectorFixture, operations: tuple[str, ...]) -> ConnectorFixture:
    """Narrow a delivered synthetic fixture to the scopes used by this recipe."""

    scopes = frozenset(
        scope for operation in operations for scope in REQUIRED_SCOPES_BY_OPERATION[operation]
    )
    return replace(fixture, scopes=scopes)


def _expect_error(code: str, action: object) -> None:
    """Run a deferred adapter action and require its stable contract error."""

    if not callable(action):
        raise TypeError("action must be callable")
    try:
        action()
    except ConnectorContractError as error:
        assert error.code == code
    else:
        raise AssertionError(f"expected connector error {code}")


def run_recipe() -> RecipeResult:
    """Execute the complete v1 journey and assert its safety properties."""

    source = _minimal_fixture(CHATGPT_SIM, SOURCE_OPERATIONS)
    collaborator = _minimal_fixture(CLAUDE_SIM, COLLABORATOR_OPERATIONS)
    tenant_b = _minimal_fixture(TENANT_B_SIM, TENANT_B_OPERATIONS)
    adapter = SyntheticLocalAdapter((source, collaborator, tenant_b))

    assert CONSENT.mode == "explicit"
    assert CONSENT.reason_code == "user_requested_memory"
    assert source.scopes == frozenset({"consent:grant", "memory:write", "connection:revoke"})
    assert collaborator.scopes == frozenset(
        {"consent:grant", "memory:read", "memory:write", "memory:delete"}
    )
    assert tenant_b.scopes == frozenset({"memory:read"})

    adapter.grant_consent(source.client_id, CONSENT)
    adapter.grant_consent(collaborator.client_id, CONSENT)
    captured = adapter.capture(
        source.client_id,
        content=CONTENT,
        consent_id=CONSENT.consent_id,
        provenance=PROVENANCE,
        idempotency_key="idem-recipe-capture-001",
    )
    assert captured.provenance == PROVENANCE
    assert captured.provenance.source_connection_id == source.connection_id

    recalled = adapter.recall(collaborator.client_id, query="outcomes")
    assert len(recalled) == 1
    assert recalled[0]["memory_id"] == captured.memory_id
    assert recalled[0]["provenance"] == PROVENANCE
    assert recalled[0]["reason_retrieved"] == "explicit_connector_semantic_match"

    # The same query from another tenant is isolated, even with a valid read scope.
    assert adapter.recall(tenant_b.client_id, query="outcomes") == ()

    updated = adapter.update(
        collaborator.client_id,
        memory_id=captured.memory_id,
        content=UPDATED_CONTENT,
        idempotency_key="idem-recipe-update-001",
    )
    assert updated.version == 2
    assert adapter.update(
        collaborator.client_id,
        memory_id=captured.memory_id,
        content=UPDATED_CONTENT,
        idempotency_key="idem-recipe-update-001",
    ) == updated

    forgotten = adapter.forget(
        collaborator.client_id,
        memory_id=captured.memory_id,
        idempotency_key="idem-recipe-forget-001",
    )
    assert forgotten == {"memory_id": captured.memory_id, "status": "forgotten"}
    assert adapter.forget(
        collaborator.client_id,
        memory_id=captured.memory_id,
        idempotency_key="idem-recipe-forget-001",
    ) == forgotten
    assert adapter.forget(
        collaborator.client_id,
        memory_id=captured.memory_id,
        idempotency_key="idem-recipe-forget-002",
    ) == {"memory_id": captured.memory_id, "status": "already_absent"}

    # Recreate a synthetic memory so revoke can prove connection scope without
    # depending on a deleted record.
    captured_again = adapter.capture(
        source.client_id,
        content=CONTENT,
        consent_id=CONSENT.consent_id,
        provenance=PROVENANCE,
        idempotency_key="idem-recipe-capture-002",
    )
    event = adapter.revoke(source.client_id, target_connection_id=source.connection_id)
    assert event["event_type"] == "connection.revoked"
    assert event["connection_id"] == source.connection_id
    assert adapter.events == (event,)
    _expect_error("connection_revoked", lambda: adapter.recall(source.client_id, query="outcomes"))
    _expect_error(
        "connection_revoked",
        lambda: adapter.capture(
            source.client_id,
            content="new synthetic capture",
            consent_id=CONSENT.consent_id,
            provenance=PROVENANCE,
            idempotency_key="idem-recipe-capture-003",
        ),
    )

    # Revoking source does not revoke another connection in the same tenant.
    surviving_recall = adapter.recall(collaborator.client_id, query="outcomes")
    assert tuple(item["memory_id"] for item in surviving_recall) == (captured_again.memory_id,)
    assert adapter.recall(tenant_b.client_id, query="outcomes") == ()

    return RecipeResult(
        contract_version=V1_CONTRACT_VERSION,
        source_scopes=tuple(sorted(source.scopes)),
        collaborator_scopes=tuple(sorted(collaborator.scopes)),
        tenant_b_scopes=tuple(sorted(tenant_b.scopes)),
        captured_memory_id=captured.memory_id,
        recalled_memory_ids=tuple(str(item["memory_id"]) for item in recalled),
        recalled_reason=str(recalled[0]["reason_retrieved"]),
        provenance_source_connection_id=captured.provenance.source_connection_id,
        updated_version=updated.version,
        forgotten_status=str(forgotten["status"]),
        tenant_b_recall_count=len(adapter.recall(tenant_b.client_id, query="outcomes")),
        revoked_connection_id=event["connection_id"],
        surviving_client_recall_ids=tuple(
            str(item["memory_id"]) for item in surviving_recall
        ),
    )


def main() -> int:
    """Print a deterministic, non-sensitive recipe result."""

    print(json.dumps(asdict(run_recipe()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
