"""Fail-closed validation shared by the hosted C01/C02 audit entrypoints."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
CYCLE_RE = re.compile(r"audit-[a-z0-9][a-z0-9-]{7,79}")
REVISION_RE = re.compile(r"umcp-cloud-staging-[a-z0-9-]+")

C01_CAPABILITIES = (
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

C02_STEPS = (
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

NEGATIVE_PROBES = (
    "unauthenticated_mcp_401",
    "authorization_code_replay_rejected",
    "old_refresh_rejected",
    "revoked_access_rejected_401",
    "forged_authority_explicit_rejection",
    "cross_tenant_explicit_rejection",
    "tombstone_non_resurrection",
)

SCOPES = ("memory:read", "memory:write", "memory:delete")


def safe_error_detail(exc: BaseException) -> dict[str, str]:
    """Return evidence-safe error classification without exception payloads."""
    code = getattr(exc, "code", None)
    return {
        "error_type": exc.__class__.__name__,
        "error_code": str(code) if code else "validation_failed",
    }


def _require_match(name: str, value: Any, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} is missing or malformed")
    if value in {"unknown", "default", "latest"}:
        raise ValueError(f"{name} uses a forbidden placeholder")
    return value


def validate_runtime_provenance(
    *,
    base_url: str,
    audit_cycle_id: str,
    audit_source_sha: str,
    baked_source_sha: str,
    audit_image_digest: str,
    server_source_sha: str,
    server_digest: str,
    server_revision: str,
) -> None:
    """Reject mutable, missing, defaulted, or contradictory audit identities."""
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("base_url must be a canonical HTTPS origin")
    _require_match("audit_cycle_id", audit_cycle_id, CYCLE_RE)
    _require_match("audit_source_sha", audit_source_sha, FULL_SHA_RE)
    _require_match("baked_source_sha", baked_source_sha, FULL_SHA_RE)
    if baked_source_sha != audit_source_sha:
        raise ValueError("audit_source_sha diverges from the SHA baked into the image")
    _require_match("audit_image_digest", audit_image_digest, DIGEST_RE)
    _require_match("server_source_sha", server_source_sha, FULL_SHA_RE)
    _require_match("server_digest", server_digest, DIGEST_RE)
    _require_match("server_revision", server_revision, REVISION_RE)


def require_exact_passes(results: Any, expected: tuple[str, ...], *, name: str) -> None:
    if not isinstance(results, dict) or set(results) != set(expected):
        raise ValueError(f"{name} result IDs are missing or incoherent")
    failed = sorted(key for key, value in results.items() if value != "PASS")
    if failed:
        raise ValueError(f"{name} contains FAIL or non-PASS results: {', '.join(failed)}")


def require_negative_passes(results: Any) -> None:
    if not isinstance(results, dict) or set(results) != set(NEGATIVE_PROBES):
        raise ValueError("negative probe IDs are missing or incoherent")
    failed = sorted(key for key, value in results.items() if value != "PASS")
    if failed:
        raise ValueError(f"negative probes failed: {', '.join(failed)}")


def validate_c01_report(report: dict[str, Any]) -> None:
    require_exact_passes(report.get("test_results"), C01_CAPABILITIES, name="C01")
    require_negative_passes(report.get("negative_results"))
    summary = report.get("summary")
    expected = {"total_capabilities": 14, "supported_count": 14, "unverified_count": 0}
    if summary != expected:
        raise ValueError("C01 summary is missing or incoherent")
    if report.get("scopes") != list(SCOPES):
        raise ValueError("C01 scopes diverge from the frozen minimum")


def validate_c02_report(report: dict[str, Any]) -> None:
    require_exact_passes(report.get("step_results"), C02_STEPS, name="C02")
    require_negative_passes(report.get("negative_results"))
    summary = report.get("summary")
    expected = {"total_steps": 15, "passed_steps": 15, "failed_steps": 0}
    if summary != expected:
        raise ValueError("C02 summary is missing or incoherent")
    if report.get("scopes") != list(SCOPES):
        raise ValueError("C02 scopes diverge from the frozen minimum")
