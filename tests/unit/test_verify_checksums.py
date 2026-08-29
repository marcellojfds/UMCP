from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.verify_checksums import compute_canonical_checksum

SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
CYCLE = "audit-20260829-deadbeef"
PROVENANCE = {
    "audit_source_sha": SHA_A,
    "server_source_sha": SHA_B,
    "server_digest": DIGEST_B,
    "server_revision": "umcp-cloud-staging-00018-f78",
    "audit_image_digest": DIGEST_A,
}
NEGATIVES = {
    "unauthenticated_mcp_401": "PASS",
    "authorization_code_replay_rejected": "PASS",
    "old_refresh_rejected": "PASS",
    "revoked_access_rejected_401": "PASS",
    "forged_authority_explicit_rejection": "PASS",
    "cross_tenant_explicit_rejection": "PASS",
    "tombstone_non_resurrection": "PASS",
}
C01_IDS = (
    "protected_resource_discovery",
    "authorization_server_discovery",
    "oauth_pkce_s256",
    "token_exchange",
    "mcp_initialize",
    "mcp_tools_list",
    "memory_write_synthetic",
    "memory_search_synthetic",
    "memory_update_synthetic",
    "memory_forget_synthetic",
    "token_refresh_rotation",
    "token_revocation",
    "forged_authority_rejection",
    "zero_leakage_redaction",
)
C02_IDS = (
    "1_discovery",
    "2_oauth_pkce_login",
    "3_mcp_initialize",
    "4_mcp_tools_list",
    "5_synthetic_write",
    "6_recall_search",
    "7_update",
    "8_forget",
    "9_tombstone_non_resurrection",
    "10_provenance_preservation",
    "11_refresh_rotation",
    "12_token_revocation",
    "13_unauthorized_after_revoke",
    "14_forged_authority_rejection",
    "15_tenant_isolation",
)


def _write_pair(directory: Path, stem: str, payload: dict) -> None:
    payload["checksum"] = compute_canonical_checksum(payload)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path = directory / f"{stem}.json"
    json_path.write_text(content, encoding="utf-8")
    file_digest = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    provenance = payload["provenance"]
    markers = [
        f"- **Audit Cycle ID:** `{payload['audit_cycle_id']}`",
        f"- **Base URL Staging:** `{payload['base_url']}`",
        f"- **Audit Source SHA:** `{provenance['audit_source_sha']}`",
        f"- **Server Source SHA:** `{provenance['server_source_sha']}`",
        f"- **Server Image Digest:** `{provenance['server_digest']}`",
        f"- **Server Active Revision:** `{provenance['server_revision']}`",
        f"- **Audit Image Digest:** `{provenance['audit_image_digest']}`",
        f"- **Report ID:** `{payload['report_id']}`",
        f"- **Checksum do Payload Canônico (SHA-256):** `{payload['checksum']}`",
        f"- **Checksum do Arquivo JSON (SHA-256):** `{file_digest}`",
    ]
    (directory / f"{stem}.md").write_text("\n".join(markers) + "\n", encoding="utf-8")


def test_stdlib_verifier_accepts_only_complete_coherent_cycle(tmp_path: Path) -> None:
    common = {
        "audit_cycle_id": CYCLE,
        "base_url": "https://staging.example.invalid",
        "provenance": dict(PROVENANCE),
    }
    c01 = {
        **common,
        "report_id": "c01-test",
        "scopes": ["memory:read", "memory:write", "memory:delete"],
        "test_results": {name: "PASS" for name in C01_IDS},
        "negative_results": dict(NEGATIVES),
        "summary": {"total_capabilities": 14, "supported_count": 14, "unverified_count": 0},
    }
    c02 = {
        **common,
        "report_id": "c02-test",
        "scopes": ["memory:read", "memory:write", "memory:delete"],
        "step_results": {name: "PASS" for name in C02_IDS},
        "negative_results": dict(NEGATIVES),
        "summary": {"total_steps": 15, "passed_steps": 15, "failed_steps": 0},
    }
    containment = {
        **common,
        "report_id": "containment-test",
        "metrics": {"active_tokens": 0, "active_codes": 0, "active_test_tenants": 0},
        "status": "PASS",
    }
    _write_pair(tmp_path, "C01-SDK-RUNNER-REPORT-20260828", c01)
    _write_pair(tmp_path, "C02-CONTROLLED-AGENT-REPORT-20260828", c02)
    _write_pair(tmp_path, "CONTAINMENT-REPORT-20260828", containment)

    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "scripts/verify_checksums.py",
            "--report-dir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    containment["metrics"] = {}
    _write_pair(tmp_path, "CONTAINMENT-REPORT-20260828", containment)
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "scripts/verify_checksums.py",
            "--report-dir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
