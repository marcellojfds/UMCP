from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.connectors.recipe import (
    COLLABORATOR_OPERATIONS,
    REQUIRED_SCOPES_BY_OPERATION,
    SOURCE_OPERATIONS,
    TENANT_B_OPERATIONS,
    V1_CONTRACT_VERSION,
    run_recipe,
)

ROOT = Path(__file__).parents[2]


def test_recipe_is_a_live_v1_specification() -> None:
    capabilities = json.loads(
        (ROOT / "docs/contracts/mcp/v1/capabilities.json").read_text()
    )
    contract_scopes = {
        item["operation"]: frozenset(item["required_scopes"])
        for item in capabilities["capabilities"]
    }
    assert capabilities["contract_version"] == V1_CONTRACT_VERSION
    assert contract_scopes == REQUIRED_SCOPES_BY_OPERATION

    result = run_recipe()

    assert result.contract_version == V1_CONTRACT_VERSION
    assert result.source_scopes == (
        "connection:revoke",
        "consent:grant",
        "memory:write",
    )
    assert result.collaborator_scopes == (
        "consent:grant",
        "memory:delete",
        "memory:read",
        "memory:write",
    )
    assert result.tenant_b_scopes == ("memory:read",)
    assert result.recalled_memory_ids == ("memory-connector-001",)
    assert result.recalled_reason == "explicit_connector_semantic_match"
    assert result.provenance_source_connection_id == "conn-chatgpt-sim"
    assert result.updated_version == 2
    assert result.forgotten_status == "forgotten"
    assert result.tenant_b_recall_count == 0
    assert result.revoked_connection_id == "conn-chatgpt-sim"
    assert result.surviving_client_recall_ids == ("memory-connector-001",)

    assert set(SOURCE_OPERATIONS) == {"consent.grant", "memory.capture", "connection.revoke"}
    assert set(COLLABORATOR_OPERATIONS) == {
        "consent.grant",
        "memory.recall",
        "memory.update",
        "memory.forget",
    }
    assert TENANT_B_OPERATIONS == ("memory.recall",)


def test_recipe_module_is_executable_without_external_services() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "examples.connectors.recipe"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    output = json.loads(completed.stdout)
    assert output["contract_version"] == V1_CONTRACT_VERSION
    assert output["tenant_b_recall_count"] == 0
    assert output["revoked_connection_id"] == "conn-chatgpt-sim"
