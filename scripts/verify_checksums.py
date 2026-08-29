#!/usr/bin/env python3
"""Deterministic verification of canonical payload checksums and file SHA-256 digests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
CYCLE_RE = re.compile(r"audit-[a-z0-9][a-z0-9-]{7,79}")
C01_IDS = {
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
}
C02_IDS = {
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
}
NEGATIVE_IDS = {
    "unauthenticated_mcp_401",
    "authorization_code_replay_rejected",
    "old_refresh_rejected",
    "revoked_access_rejected_401",
    "forged_authority_explicit_rejection",
    "cross_tenant_explicit_rejection",
    "tombstone_non_resurrection",
}
SCOPES = ["memory:read", "memory:write", "memory:delete"]


def compute_canonical_checksum(payload: dict) -> str:
    """Compute the report checksum without importing the application package."""
    clean_payload = {key: value for key, value in payload.items() if key != "checksum"}
    canonical_bytes = json.dumps(clean_payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"


def compute_file_sha256(file_path: Path) -> str:
    """Compute the SHA-256 digest of a report file using only the standard library."""
    return f"sha256:{hashlib.sha256(file_path.read_bytes()).hexdigest()}"


def verify_report(json_path: Path, md_path: Path) -> bool:
    print(f"[*] Verifying {json_path.name} and {md_path.name}...")
    if not json_path.exists() or not md_path.exists():
        print(f"    [!] Error: Files {json_path} or {md_path} missing.", file=sys.stderr)
        return False

    try:
        raw_json = json_path.read_text(encoding="utf-8")
        data = json.loads(raw_json)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"    [!] Invalid JSON artifact: {exc.__class__.__name__}", file=sys.stderr)
        return False
    if not isinstance(data, dict):
        print("    [!] JSON artifact must contain an object.", file=sys.stderr)
        return False

    recorded_canonical = data.get("checksum")
    computed_canonical = compute_canonical_checksum(data)
    if recorded_canonical != computed_canonical:
        print("    [!] Canonical checksum mismatch:", file=sys.stderr)
        print(f"        Recorded: {recorded_canonical}", file=sys.stderr)
        print(f"        Computed: {computed_canonical}", file=sys.stderr)
        return False
    print(f"    [+] Canonical payload checksum matches: {computed_canonical}")

    actual_file_sha256 = compute_file_sha256(json_path)
    md_content = md_path.read_text(encoding="utf-8")

    expected_file_marker = f"- **Checksum do Arquivo JSON (SHA-256):** `{actual_file_sha256}`"
    if expected_file_marker not in md_content:
        print("    [!] Markdown file_sha256 marker mismatch against disk file:", file=sys.stderr)
        print(f"        Actual file SHA-256: {actual_file_sha256}", file=sys.stderr)
        return False
    print(f"    [+] Markdown references exact file SHA-256: {actual_file_sha256}")

    expected_canonical_marker = (
        f"- **Checksum do Payload Canônico (SHA-256):** `{computed_canonical}`"
    )
    if expected_canonical_marker not in md_content:
        print("    [!] Markdown canonical checksum marker mismatch:", file=sys.stderr)
        print(f"        Expected: {expected_canonical_marker}", file=sys.stderr)
        return False
    print(f"    [+] Markdown references exact canonical payload checksum: {computed_canonical}")

    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        print("    [!] JSON provenance object is missing.", file=sys.stderr)
        return False
    expected_markers = (
        f"- **Audit Cycle ID:** `{data.get('audit_cycle_id')}`",
        f"- **Base URL Staging:** `{data.get('base_url')}`",
        f"- **Audit Source SHA:** `{provenance.get('audit_source_sha')}`",
        f"- **Server Source SHA:** `{provenance.get('server_source_sha')}`",
        f"- **Server Image Digest:** `{provenance.get('server_digest')}`",
        f"- **Server Active Revision:** `{provenance.get('server_revision')}`",
        f"- **Audit Image Digest:** `{provenance.get('audit_image_digest')}`",
        f"- **Report ID:** `{data.get('report_id')}`",
    )
    if any(marker not in md_content for marker in expected_markers):
        print("    [!] Markdown provenance marker is missing or divergent.", file=sys.stderr)
        return False

    return True


def _valid_provenance(report: dict) -> bool:
    provenance = report.get("provenance")
    if not isinstance(provenance, dict):
        return False
    return (
        bool(FULL_SHA_RE.fullmatch(str(provenance.get("audit_source_sha", ""))))
        and bool(FULL_SHA_RE.fullmatch(str(provenance.get("server_source_sha", ""))))
        and bool(DIGEST_RE.fullmatch(str(provenance.get("server_digest", ""))))
        and bool(DIGEST_RE.fullmatch(str(provenance.get("audit_image_digest", ""))))
        and isinstance(provenance.get("server_revision"), str)
        and "latest" not in str(provenance).lower()
        and "unknown" not in str(provenance).lower()
        and "default" not in str(provenance).lower()
    )


def validate_schema(report_dir: Path) -> bool:
    names = {
        "c01": "C01-SDK-RUNNER-REPORT-20260828.json",
        "c02": "C02-CONTROLLED-AGENT-REPORT-20260828.json",
        "containment": "CONTAINMENT-REPORT-20260828.json",
    }
    try:
        reports = {
            key: json.loads((report_dir / name).read_text(encoding="utf-8"))
            for key, name in names.items()
        }
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[!] Schema input invalid: {exc.__class__.__name__}", file=sys.stderr)
        return False
    if not all(isinstance(value, dict) for value in reports.values()):
        print("[!] Every report must be a JSON object.", file=sys.stderr)
        return False

    c01, c02, containment = reports["c01"], reports["c02"], reports["containment"]
    cycle = c01.get("audit_cycle_id")
    if not isinstance(cycle, str) or not CYCLE_RE.fullmatch(cycle):
        print("[!] audit_cycle_id is missing or malformed.", file=sys.stderr)
        return False
    common = ("audit_cycle_id", "base_url", "provenance")
    if any(report.get(field) != c01.get(field) for report in reports.values() for field in common):
        print("[!] Reports do not share one audit cycle and provenance tuple.", file=sys.stderr)
        return False
    if not all(_valid_provenance(report) for report in reports.values()):
        print("[!] Provenance is missing, mutable, defaulted, or malformed.", file=sys.stderr)
        return False
    if not str(c01.get("base_url", "")).startswith("https://"):
        print("[!] base_url must be HTTPS.", file=sys.stderr)
        return False

    c01_results = c01.get("test_results")
    c02_results = c02.get("step_results")
    if (
        not isinstance(c01_results, dict)
        or set(c01_results) != C01_IDS
        or set(c01_results.values()) != {"PASS"}
    ):
        print("[!] C01 IDs or statuses are incoherent.", file=sys.stderr)
        return False
    if c01.get("summary") != {
        "total_capabilities": 14,
        "supported_count": 14,
        "unverified_count": 0,
    }:
        print("[!] C01 totals are incoherent.", file=sys.stderr)
        return False
    if (
        not isinstance(c02_results, dict)
        or set(c02_results) != C02_IDS
        or set(c02_results.values()) != {"PASS"}
    ):
        print("[!] C02 IDs or statuses are incoherent.", file=sys.stderr)
        return False
    if c02.get("summary") != {"total_steps": 15, "passed_steps": 15, "failed_steps": 0}:
        print("[!] C02 totals are incoherent.", file=sys.stderr)
        return False
    if c01.get("scopes") != SCOPES or c02.get("scopes") != SCOPES:
        print("[!] Frozen scopes are missing or incoherent.", file=sys.stderr)
        return False
    for report in (c01, c02):
        negatives = report.get("negative_results")
        if (
            not isinstance(negatives, dict)
            or set(negatives) != NEGATIVE_IDS
            or set(negatives.values()) != {"PASS"}
        ):
            print("[!] Required negative probes are missing or not PASS.", file=sys.stderr)
            return False

    metrics = containment.get("metrics")
    required_metrics = {"active_tokens", "active_codes", "active_test_tenants"}
    if not isinstance(metrics, dict) or set(metrics) != required_metrics:
        print(
            "[!] Containment metric map is empty, missing, or has unexpected keys.", file=sys.stderr
        )
        return False
    if any(type(metrics[key]) is not int or metrics[key] != 0 for key in required_metrics):
        print("[!] Containment metrics must be exact integer zero values.", file=sys.stderr)
        return False
    if containment.get("status") != "PASS":
        print("[!] Containment status is not PASS.", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=repo_root / "docs/handoffs/roadmap",
    )
    args = parser.parse_args()
    report_dir = args.report_dir
    reports = [
        (
            report_dir / "C01-SDK-RUNNER-REPORT-20260828.json",
            report_dir / "C01-SDK-RUNNER-REPORT-20260828.md",
        ),
        (
            report_dir / "C02-CONTROLLED-AGENT-REPORT-20260828.json",
            report_dir / "C02-CONTROLLED-AGENT-REPORT-20260828.md",
        ),
        (
            report_dir / "CONTAINMENT-REPORT-20260828.json",
            report_dir / "CONTAINMENT-REPORT-20260828.md",
        ),
    ]

    all_ok = validate_schema(report_dir)
    for j_path, m_path in reports:
        if not verify_report(j_path, m_path):
            all_ok = False

    if not all_ok:
        print("\n[!] VERIFICATION FAILED", file=sys.stderr)
        return 1

    print("\n[+] ALL REPORT CHECKSUMS AND DISK HASHES DETERMINISTICALLY VERIFIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
