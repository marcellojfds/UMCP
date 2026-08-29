from __future__ import annotations

import pytest

from omp.sdk.agent import _require_explicit_cross_tenant_denial
from omp.sdk.audit_contract import (
    C01_CAPABILITIES,
    C02_STEPS,
    NEGATIVE_PROBES,
    validate_c01_report,
    validate_c02_report,
    validate_runtime_provenance,
)
from omp.sdk.client import ProtocolError

SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
NEGATIVES = {name: "PASS" for name in NEGATIVE_PROBES}


def test_runtime_provenance_requires_baked_sha_match_and_immutable_digests() -> None:
    validate_runtime_provenance(
        base_url="https://staging.example.invalid",
        audit_cycle_id="audit-20260829-deadbeef",
        audit_source_sha=SHA_A,
        baked_source_sha=SHA_A,
        audit_image_digest=DIGEST_A,
        server_source_sha=SHA_B,
        server_digest=DIGEST_B,
        server_revision="umcp-cloud-staging-00018-f78",
    )

    with pytest.raises(ValueError):
        validate_runtime_provenance(
            base_url="https://staging.example.invalid",
            audit_cycle_id="audit-20260829-deadbeef",
            audit_source_sha=SHA_A,
            baked_source_sha=SHA_B,
            audit_image_digest=DIGEST_A,
            server_source_sha=SHA_B,
            server_digest=DIGEST_B,
            server_revision="umcp-cloud-staging-00018-f78",
        )


def test_c01_and_c02_require_exact_ids_totals_and_negatives() -> None:
    c01 = {
        "test_results": {name: "PASS" for name in C01_CAPABILITIES},
        "negative_results": dict(NEGATIVES),
        "summary": {"total_capabilities": 14, "supported_count": 14, "unverified_count": 0},
        "scopes": ["memory:read", "memory:write", "memory:delete"],
    }
    c02 = {
        "step_results": {name: "PASS" for name in C02_STEPS},
        "negative_results": dict(NEGATIVES),
        "summary": {"total_steps": 15, "passed_steps": 15, "failed_steps": 0},
        "scopes": ["memory:read", "memory:write", "memory:delete"],
    }
    validate_c01_report(c01)
    validate_c02_report(c02)

    c01["test_results"].pop("mcp_initialize")
    with pytest.raises(ValueError):
        validate_c01_report(c01)

    c02["negative_results"] = {}
    with pytest.raises(ValueError):
        validate_c02_report(c02)


def test_cross_tenant_denial_rejects_generic_exceptions() -> None:
    def explicit() -> None:
        raise ProtocolError("not_found", "not found")

    def generic() -> None:
        raise RuntimeError("network failed")

    assert _require_explicit_cross_tenant_denial(explicit) == "not_found"
    with pytest.raises(RuntimeError):
        _require_explicit_cross_tenant_denial(generic)
