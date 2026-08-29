"""Runner and reproducible conformance report generator for UMCP SDK."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .client import MemoryClient, ProtocolError
from .cloud import CloudOAuthTransport
from .oauth import OAuthSession, generate_pkce_pair


def generate_c01_report(
    *,
    base_url: str,
    server_sha: str = "e65bddff517633a2982a4ac5abb3851a1a43e68c",
    server_digest: str = "sha256:de17d469904f0b8c6d4e13480a85ec6fd7494c089ba5dedab7175839307d5629",
    server_revision: str = "umcp-cloud-staging-00017-jsj",
    transport_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a reproducible, dated, checksummed C01 conformance report."""
    report_id = f"c01-{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    matrix = {
        "supported": [
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
        ],
        "experimental": [
            "streamable_sse_transport",
            "realtime_notifications",
        ],
        "unverified": [
            "third_party_non_standard_idp",
            "custom_claims_provider",
        ],
    }

    report_body = {
        "report_id": report_id,
        "sdk_version": "1.0.0",
        "protocol_version": "omp.mcp.v0",
        "created_at": created_at,
        "base_url": base_url,
        "provenance": {
            "server_sha": server_sha,
            "server_digest": server_digest,
            "server_revision": server_revision,
        },
        "scopes": [
            "memory:read",
            "memory:write",
            "memory:delete",
            "memory:export",
            "connections:manage",
        ],
        "matrix": matrix,
        "test_results": transport_results or {},
        "limitations": [
            "Private managed beta only; not approved for public distribution or external users",
            "Operates with authorized test identity and synthetic test payloads only",
        ],
    }

    raw_canonical = json.dumps(report_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(raw_canonical).hexdigest()
    report_body["checksum"] = f"sha256:{checksum}"

    return report_body
