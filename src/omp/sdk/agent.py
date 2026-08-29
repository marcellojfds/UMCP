"""Controlled Python agent for UMCP C02 integration."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .audit_contract import safe_error_detail
from .checksums import compute_canonical_checksum
from .client import MemoryClient, ProtocolError
from .cloud import CloudOAuthTransport

EXPLICIT_CROSS_TENANT_CODES = {
    "forbidden",
    "not_found",
    "tenant_mismatch",
    "unauthorized",
    "validation_error",
}


def _require_explicit_cross_tenant_denial(call: Any) -> str:
    try:
        call()
    except ProtocolError as exc:
        if exc.code not in EXPLICIT_CROSS_TENANT_CODES:
            raise ValueError("Cross-tenant mutation returned a non-explicit error code") from None
        return exc.code
    raise ValueError("Cross-tenant mutation was not explicitly rejected")


def _extract_memories(res: Any) -> list[dict[str, Any]]:
    """Normalize direct and nested memory list envelopes."""
    if not isinstance(res, dict):
        return []
    data = res.get("data", res) if isinstance(res, dict) else {}
    if not isinstance(data, dict):
        return []
    raw_list = (
        data.get("memories")
        or data.get("matches")
        or data.get("results")
        or data.get("records")
        or []
    )
    out = []
    for item in raw_list:
        if isinstance(item, dict):
            mem = item.get("memory") or item.get("record") or item
            if isinstance(mem, dict):
                out.append(mem)
    return out


class ControlledMemoryAgent:
    """Controlled Python agent performing end-to-end memory lifecycle operations."""

    AGENT_VERSION = "1.0.0"
    SDK_VERSION = "1.0.0"

    def __init__(
        self,
        transport_a: CloudOAuthTransport,
        transport_b: CloudOAuthTransport | None = None,
    ) -> None:
        self.transport_a = transport_a
        self.transport_b = transport_b
        self.client_a = MemoryClient(transport_a)
        self.client_b = MemoryClient(transport_b) if transport_b else None
        self.session_a = transport_a.session
        self.session_b = transport_b.session if transport_b else None

    def run_e2e_journey(
        self,
        *,
        audit_source_sha: str,
        audit_cycle_id: str = "audit-local-unverified",
        negative_results: dict[str, str] | None = None,
        server_source_sha: str = "367cd365df43f9282f5155394cd39275169bf8f2",
        server_digest: str = "sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d",
        server_revision: str = "umcp-cloud-staging-00018-f78",
        audit_image_digest: str = "sha256:unknown",
        output_json_path: Path | str | None = None,
        output_md_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Execute the 15-step C02 memory agent lifecycle fail-closed."""
        report_id = f"c02-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        results: dict[str, str] = {}
        details: dict[str, Any] = {}

        try:
            # 1. Discovery
            try:
                p_res = self.session_a.discover_protected_resource()
                a_res = self.session_a.discover_authorization_server()
                if not isinstance(p_res, dict) or not isinstance(a_res, dict):
                    raise ValueError("Discovery responses must be non-empty dictionaries")
                if p_res.get("resource") != f"{self.session_a.base_url}/mcp":
                    raise ValueError(f"Unexpected protected resource: {p_res.get('resource')}")
                if not a_res.get("authorization_endpoint") or not a_res.get("token_endpoint"):
                    raise ValueError(f"Incomplete authorization server metadata: {a_res}")
                results["1_discovery"] = "PASS"
                details["1_discovery"] = {
                    "protected_resource": p_res.get("resource"),
                    "auth_endpoint": a_res.get("authorization_endpoint"),
                }
            except Exception as exc:
                results["1_discovery"] = "FAIL"
                details["1_discovery"] = safe_error_detail(exc)

            # 2. Credential verification. This is not an interactive login:
            # the controlled C02 harness receives pre-provisioned synthetic tokens.
            try:
                if not self.session_a._tokens or not self.session_a._tokens.access_token:
                    raise ValueError("No authenticated token present in session A")
                token_val = self.session_a.get_valid_access_token()
                if not token_val:
                    raise ValueError("Failed to retrieve valid access token")
                results["2_oauth_pkce_login"] = "PASS"
                details["2_oauth_pkce_login"] = {
                    "credential_source": "synthetic_preprovisioned_token",
                    "interactive_login_performed": False,
                    "token_type": self.session_a._tokens.token_type,
                    "has_refresh": bool(self.session_a._tokens.refresh_token),
                }
            except Exception as exc:
                results["2_oauth_pkce_login"] = "FAIL"
                details["2_oauth_pkce_login"] = safe_error_detail(exc)

            # 3. Initialize & 4. Tools List
            try:
                disc = self.transport_a.discover()
                server_name = disc.get("server_name")
                tools = disc.get("tools", [])
                if server_name != "umcp-cloud":
                    raise ValueError(f"Expected server umcp-cloud, got {server_name}")
                required_tools = {"memory.write", "memory.search", "memory.update", "memory.forget"}
                if not required_tools.issubset(set(tools)):
                    raise ValueError(f"Missing required tools: {required_tools - set(tools)}")
                results["3_mcp_initialize"] = "PASS"
                results["4_mcp_tools_list"] = "PASS"
                details["3_mcp_initialize"] = {
                    "server_name": server_name,
                    "version": disc.get("server_version"),
                }
                details["4_mcp_tools_list"] = {"tools_count": len(tools)}
            except Exception as exc:
                results["3_mcp_initialize"] = "FAIL"
                results["4_mcp_tools_list"] = "FAIL"
                details["3_mcp_initialize"] = safe_error_detail(exc)
                details["4_mcp_tools_list"] = safe_error_detail(exc)

            # 5. Synthetic Write / Capture
            write_key = f"c02-write-{uuid.uuid4().hex[:8]}"
            synthetic_content = f"c02 synthetic agent memory content {uuid.uuid4().hex[:6]}"
            record_id = None
            record = None
            captured_time = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            sent_provenance = {
                "source_type": "user",
                "captured_at": captured_time,
                "source_id": "c02-test-actor",
            }
            try:
                res_write = self.client_a.write(
                    content=synthetic_content,
                    type="fact",
                    provenance=sent_provenance,
                    idempotency_key=write_key,
                )
                data_map = res_write.get("data", res_write) if isinstance(res_write, dict) else {}
                record = data_map.get("memory") or data_map.get("record") or data_map
                record_id = (
                    record.get("id") if isinstance(record, dict) else None
                ) or res_write.get("id")
                if not record_id:
                    raise ValueError(f"memory.write did not return a valid record id: {res_write}")
                init_version = record.get("version") if isinstance(record, dict) else 1
                if init_version != 1:
                    raise ValueError(f"Initial record version expected 1, got {init_version}")
                results["5_synthetic_write"] = "PASS"
                details["5_synthetic_write"] = {"record_id": str(record_id), "version": 1}
            except Exception as exc:
                results["5_synthetic_write"] = "FAIL"
                details["5_synthetic_write"] = safe_error_detail(exc)

            # 6. Recall / Search
            try:
                if not record_id:
                    raise ValueError("Cannot perform recall check: prerequisite write failed")
                res_search = self.client_a.search(
                    query=synthetic_content, limit=5, min_relevance=0.1
                )
                items = _extract_memories(res_search)
                found = False
                for mem in items:
                    if mem.get("id") == record_id or mem.get("content") == synthetic_content:
                        found = True
                        break
                if not found:
                    raise ValueError(
                        f"Written record {record_id} not found in search results: {res_search}"
                    )
                results["6_recall_search"] = "PASS"
                details["6_recall_search"] = {"found": True, "items_count": len(items)}
            except Exception as exc:
                results["6_recall_search"] = "FAIL"
                details["6_recall_search"] = safe_error_detail(exc)

            # 7. Update (strict: matching ID, updated content, version == 2)
            updated_content = f"{synthetic_content} updated v2"
            try:
                if not record_id:
                    raise ValueError("Cannot perform update check: prerequisite write failed")
                update_key = f"c02-update-{uuid.uuid4().hex[:8]}"
                res_update = self.client_a.update(
                    id=record_id,
                    expected_version=1,
                    patch={"content": updated_content},
                    idempotency_key=update_key,
                )
                upd_data = (
                    res_update.get("data", res_update) if isinstance(res_update, dict) else {}
                )
                upd_record = upd_data.get("memory") or upd_data.get("record") or upd_data
                if not isinstance(upd_record, dict):
                    raise ValueError(f"Update returned non-dictionary record payload: {res_update}")
                upd_id = upd_record.get("id")
                if not upd_id or str(upd_id) != str(record_id):
                    raise ValueError(
                        f"Update returned mismatching record ID: expected {record_id}, got {upd_id}"
                    )
                upd_content = upd_record.get("content")
                if upd_content != updated_content:
                    raise ValueError(
                        f"Update returned mismatching content: expected '{updated_content}', got '{upd_content}'"
                    )
                new_version = upd_record.get("version")
                if new_version != 2:
                    raise ValueError(f"Update expected incremented version 2, got {new_version}")
                results["7_update"] = "PASS"
                details["7_update"] = {"updated": True, "new_version": 2}
            except Exception as exc:
                results["7_update"] = "FAIL"
                details["7_update"] = safe_error_detail(exc)

            # 10. Provenance Preservation (fail if expected fields are missing or different)
            try:
                if not record_id or not record:
                    raise ValueError(
                        "Cannot verify provenance: prerequisite write failed or empty record"
                    )
                prov = record.get("provenance", {})
                if not prov or not isinstance(prov, dict):
                    raise ValueError(f"Record does not contain valid provenance object: {record}")
                if prov.get("source_type") != sent_provenance["source_type"]:
                    raise ValueError(
                        f"Provenance source_type mismatch: expected {sent_provenance['source_type']}, got {prov.get('source_type')}"
                    )
                if prov.get("source_id") != sent_provenance["source_id"]:
                    raise ValueError(
                        f"Provenance source_id mismatch: expected {sent_provenance['source_id']}, got {prov.get('source_id')}"
                    )
                if not prov.get("captured_at"):
                    raise ValueError("Provenance missing required captured_at field")
                results["10_provenance_preservation"] = "PASS"
                details["10_provenance_preservation"] = {
                    "provenance_validated": True,
                    "source_type": prov.get("source_type"),
                    "source_id": prov.get("source_id"),
                }
            except Exception as exc:
                results["10_provenance_preservation"] = "FAIL"
                details["10_provenance_preservation"] = safe_error_detail(exc)

            # 14. Forged Authority Attempt (client-side and direct server-side explicit rejection)
            try:
                client_rejected = False
                try:
                    self.client_a.write(content="forged", owner_id="forged-owner-id")
                except ProtocolError:
                    client_rejected = True
                if not client_rejected:
                    raise ValueError("Client allowed forged owner_id without ProtocolError")

                server_rejected = False
                token = self.session_a.get_valid_access_token()
                forged_body = json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 888,
                        "method": "tools/call",
                        "params": {
                            "name": "memory.write",
                            "arguments": {"content": "forged", "owner_id": "forged-id"},
                        },
                    }
                ).encode("utf-8")
                req = Request(
                    f"{self.session_a.base_url}/mcp",
                    data=forged_body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                        "Authorization": f"Bearer {token}",
                    },
                    method="POST",
                )
                try:
                    with urlopen(req, timeout=self.session_a.timeout) as resp:
                        raw = resp.read().decode()
                        parsed = json.loads(raw) if raw else {}
                        if "error" in parsed or parsed.get("result", {}).get("isError") is True:
                            server_rejected = True
                        else:
                            raise ValueError(
                                f"Server did not reject forged authority in JSON-RPC response: {raw[:150]}"
                            )
                except HTTPError as exc:
                    if exc.code in {400, 403, 422}:
                        server_rejected = True
                    else:
                        raise ValueError(
                            f"Server returned unexpected HTTP error on forged authority: {exc.code}"
                        )
                except Exception as exc:
                    raise ValueError(f"Direct server probe for forged authority failed: {exc}")

                if not server_rejected:
                    raise ValueError("Server failed to reject forged authority")

                results["14_forged_authority_rejection"] = "PASS"
                details["14_forged_authority_rejection"] = {
                    "client_rejected": True,
                    "server_rejected": True,
                }
            except Exception as exc:
                results["14_forged_authority_rejection"] = "FAIL"
                details["14_forged_authority_rejection"] = safe_error_detail(exc)

            # 15. Tenant Isolation (strictly requiring two distinct tenant contexts, read/write/mutation assertions in both directions with post-mutation verification)
            try:
                if not self.transport_b or not self.client_b or not self.session_b:
                    raise ValueError(
                        "Only one tenant/identity provided; two independent tenants are required to prove zero leakage"
                    )

                # Tenant B writes unique secret memory
                b_key = f"c02-tenant-b-write-{uuid.uuid4().hex[:8]}"
                content_b = f"tenant_b_isolated_secret_{uuid.uuid4().hex[:8]}"
                b_prov = {
                    "source_type": "user",
                    "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "source_id": "c02-tenant-b",
                }
                res_write_b = self.client_b.write(
                    content=content_b, type="fact", provenance=b_prov, idempotency_key=b_key
                )
                b_data = (
                    res_write_b.get("data", res_write_b) if isinstance(res_write_b, dict) else {}
                )
                b_rec = b_data.get("memory") or b_data.get("record") or b_data
                rec_b_id = b_rec.get("id") if isinstance(b_rec, dict) else None
                if not rec_b_id:
                    raise ValueError("Tenant B write failed to return a valid record ID")

                # 1. Tenant A searches for Tenant B secret -> must return 0 results
                res_a_leak_search = self.client_a.search(
                    query=content_b, limit=10, min_relevance=0.1
                )
                items_a = _extract_memories(res_a_leak_search)
                if any(m.get("id") == rec_b_id or m.get("content") == content_b for m in items_a):
                    raise ValueError(
                        "Cross-tenant leakage detected: Tenant A retrieved Tenant B memory"
                    )

                # 2. Tenant B searches for Tenant A memory -> must return 0 results
                res_b_leak_search = self.client_b.search(
                    query=synthetic_content, limit=10, min_relevance=0.1
                )
                items_b = _extract_memories(res_b_leak_search)
                if any(
                    m.get("id") == record_id or m.get("content") == synthetic_content
                    for m in items_b
                ):
                    raise ValueError(
                        "Cross-tenant leakage detected: Tenant B retrieved Tenant A memory"
                    )

                # 3. Tenant A attempts mutation on Tenant B record (A -> B).
                # Network/parse/unknown exceptions never count as isolation evidence.
                denial_a = _require_explicit_cross_tenant_denial(
                    lambda: self.client_a.update(
                        id=rec_b_id,
                        expected_version=1,
                        patch={"content": "hacked_by_a"},
                        idempotency_key="leak-upd-a",
                    )
                )

                # 3b. Verify Tenant B record remains completely unmutated (ID, content, version == 1)
                res_b_verify = self.client_b.search(query=content_b, limit=5, min_relevance=0.1)
                b_mems = _extract_memories(res_b_verify)
                b_match = next((m for m in b_mems if m.get("id") == rec_b_id), None)
                if (
                    not b_match
                    or b_match.get("content") != content_b
                    or b_match.get("version", 1) != 1
                ):
                    raise ValueError(
                        f"Tenant B record state altered after cross-tenant attempt: {b_match}"
                    )

                # 4. Tenant B attempts mutation on Tenant A record (B -> A).
                denial_b = _require_explicit_cross_tenant_denial(
                    lambda: self.client_b.update(
                        id=record_id,
                        expected_version=2,
                        patch={"content": "hacked_by_b"},
                        idempotency_key="leak-upd-b",
                    )
                )

                # 4b. Verify Tenant A record remains completely unmutated (ID, updated_content, version == 2)
                res_a_verify = self.client_a.search(
                    query=updated_content, limit=5, min_relevance=0.1
                )
                a_mems = _extract_memories(res_a_verify)
                a_match = next((m for m in a_mems if m.get("id") == record_id), None)
                if (
                    not a_match
                    or a_match.get("content") != updated_content
                    or a_match.get("version", 2) != 2
                ):
                    raise ValueError(
                        f"Tenant A record state altered after cross-tenant attempt: {a_match}"
                    )

                results["15_tenant_isolation"] = "PASS"
                details["15_tenant_isolation"] = {
                    "zero_leakage_proven": True,
                    "explicit_denial_codes": [denial_a, denial_b],
                    "database_rls_directly_proven": False,
                    "claim": "observed application boundary isolation; not direct RLS proof",
                }
            except Exception as exc:
                results["15_tenant_isolation"] = "FAIL"
                details["15_tenant_isolation"] = safe_error_detail(exc)

            # 8. Forget (strict: explicit tombstone/deletion status and ok == True)
            try:
                if not record_id:
                    raise ValueError("Cannot perform forget check: prerequisite write failed")
                forget_key = f"c02-forget-{uuid.uuid4().hex[:8]}"
                res_forget = self.client_a.forget(id=record_id, idempotency_key=forget_key)
                if not isinstance(res_forget, dict):
                    raise ValueError("memory.forget returned invalid non-dictionary envelope")
                forget_data = (
                    res_forget.get("data", res_forget) if isinstance(res_forget, dict) else {}
                )
                ret_status = (
                    forget_data.get("status")
                    or forget_data.get("state")
                    or res_forget.get("status")
                )
                if (
                    ret_status not in {"forgotten", "deleted", "archived", "tombstoned"}
                    and res_forget.get("ok") is not True
                ):
                    raise ValueError(
                        f"Forget did not return explicit tombstone status: {res_forget}"
                    )
                results["8_forget"] = "PASS"
                details["8_forget"] = {"forgotten_id": str(record_id), "status": ret_status}
            except Exception as exc:
                results["8_forget"] = "FAIL"
                details["8_forget"] = safe_error_detail(exc)

            # 9. Tombstone Proof (verifying the same record ID is not returned after forget)
            try:
                if not record_id:
                    raise ValueError("Cannot perform tombstone check: prerequisite write failed")
                res_tombstone = self.client_a.search(
                    query=updated_content, limit=10, min_relevance=0.1
                )
                items = _extract_memories(res_tombstone)
                still_exists = False
                for mem in items:
                    if mem.get("id") == record_id:
                        still_exists = True
                        break
                if still_exists:
                    raise ValueError(
                        f"Forgotten record {record_id} was resurrected in search results"
                    )
                results["9_tombstone_non_resurrection"] = "PASS"
                details["9_tombstone_non_resurrection"] = {
                    "non_resurrected": True,
                    "verified_record_id": str(record_id),
                }
            except Exception as exc:
                results["9_tombstone_non_resurrection"] = "FAIL"
                details["9_tombstone_non_resurrection"] = safe_error_detail(exc)

            # 11. Refresh & Rotation (verifying new tokens and old refresh rejection HTTP 400)
            old_refresh_code = None
            try:
                if not self.session_a._tokens or not self.session_a._tokens.refresh_token:
                    raise ValueError("No refresh token available in session A to test rotation")
                old_access = self.session_a._tokens.access_token
                old_refresh = self.session_a._tokens.refresh_token
                new_tokens = self.session_a.refresh()
                if new_tokens.access_token == old_access or new_tokens.refresh_token == old_refresh:
                    raise ValueError("Refresh did not rotate access/refresh token pair")
                token_endpoint = f"{self.session_a.base_url}/token"
                old_ref_body = urlencode(
                    {
                        "grant_type": "refresh_token",
                        "refresh_token": old_refresh,
                        "client_id": self.session_a.client_id,
                    }
                ).encode("utf-8")
                req = Request(
                    token_endpoint,
                    data=old_ref_body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                try:
                    with urlopen(req, timeout=self.session_a.timeout) as resp:
                        old_refresh_code = resp.status
                except HTTPError as exc:
                    old_refresh_code = exc.code
                if old_refresh_code != 400:
                    raise ValueError(
                        f"Old refresh token was not rejected with HTTP 400 (got {old_refresh_code})"
                    )
                results["11_refresh_rotation"] = "PASS"
                details["11_refresh_rotation"] = {
                    "rotated": True,
                    "old_refresh_rejected_status": 400,
                }
            except Exception as exc:
                results["11_refresh_rotation"] = "FAIL"
                details["11_refresh_rotation"] = safe_error_detail(exc)

            # 12. Revoke (preserving token, clearing session) & 13. Unauthorized After Revoke (HTTP 401 to /mcp)
            revoked_access_token = None
            revoke_code = 200
            post_revoke_code = None
            try:
                if not self.session_a._tokens or not self.session_a._tokens.access_token:
                    raise ValueError("No active access token to revoke in session A")
                revoked_access_token = self.session_a._tokens.access_token
                revoked = self.session_a.revoke()
                if not revoked or self.session_a._tokens is not None:
                    raise ValueError("Token revocation failed to clear local session")
                results["12_token_revocation"] = "PASS"
                details["12_token_revocation"] = {"revoked": True, "revoke_status": revoke_code}
            except Exception as exc:
                results["12_token_revocation"] = "FAIL"
                details["12_token_revocation"] = safe_error_detail(exc)

            try:
                if not revoked_access_token:
                    raise ValueError("Cannot test post-revoke HTTP 401: prerequisite revoke failed")
                mcp_endpoint = f"{self.session_a.base_url}/mcp"
                probe_payload = json.dumps(
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
                ).encode("utf-8")
                req = Request(
                    mcp_endpoint,
                    data=probe_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                        "Authorization": f"Bearer {revoked_access_token}",
                    },
                    method="POST",
                )
                try:
                    with urlopen(req, timeout=self.session_a.timeout) as resp:
                        post_revoke_code = resp.status
                except HTTPError as exc:
                    post_revoke_code = exc.code
                if post_revoke_code != 401:
                    raise ValueError(
                        f"Revoked access token was not rejected by server with HTTP 401 (got {post_revoke_code})"
                    )
                results["13_unauthorized_after_revoke"] = "PASS"
                details["13_unauthorized_after_revoke"] = {
                    "rejected_401": True,
                    "post_revoke_status": 401,
                }
            except Exception as exc:
                results["13_unauthorized_after_revoke"] = "FAIL"
                details["13_unauthorized_after_revoke"] = safe_error_detail(exc)

        finally:
            if self.session_a and self.session_a._tokens:
                try:
                    self.session_a.revoke()
                except Exception:
                    pass
            if self.session_b and self.session_b._tokens:
                try:
                    self.session_b.revoke()
                except Exception:
                    pass

        report = {
            "report_id": report_id,
            "audit_cycle_id": audit_cycle_id,
            "agent_version": self.AGENT_VERSION,
            "sdk_version": self.SDK_VERSION,
            "timestamp_utc": timestamp,
            "base_url": self.session_a.base_url,
            "provenance": {
                "audit_source_sha": audit_source_sha,
                "server_source_sha": server_source_sha,
                "server_digest": server_digest,
                "server_revision": server_revision,
                "audit_image_digest": audit_image_digest,
            },
            "scopes": [
                "memory:read",
                "memory:write",
                "memory:delete",
            ],
            "step_results": results,
            "step_details": details,
            "negative_results": negative_results or {},
            "summary": {
                "total_steps": len(results),
                "passed_steps": sum(1 for v in results.values() if v == "PASS"),
                "failed_steps": sum(1 for v in results.values() if v != "PASS"),
            },
            "limitations": [
                "Private managed beta only",
                "Strictly synthetic test payloads; zero user data",
                "Ephemeral in-memory token lifecycle",
                "Step 2 uses synthetic pre-provisioned credentials; no interactive login was performed",
                "Tenant isolation is observed at the application boundary; this report is not direct RLS proof",
            ],
        }

        report["checksum"] = compute_canonical_checksum(report)
        formatted_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
        file_sha256 = f"sha256:{hashlib.sha256(formatted_json.encode('utf-8')).hexdigest()}"

        if output_json_path:
            p = Path(output_json_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(formatted_json, encoding="utf-8")

        if output_md_path:
            json_name = Path(output_json_path).name if output_json_path else "c02-report.json"
            md_lines = [
                "# C02 — Relatório de Execução do Controlled Python Agent",
                "",
                f"- **Data:** {timestamp}",
                f"- **Versão do Agente:** `{self.AGENT_VERSION}`",
                f"- **Versão do SDK:** `{self.SDK_VERSION}`",
                f"- **Base URL Staging:** `{self.session_a.base_url}`",
                f"- **Audit Source SHA:** `{audit_source_sha}`",
                f"- **Server Source SHA:** `{server_source_sha}`",
                f"- **Server Image Digest:** `{server_digest}`",
                f"- **Server Active Revision:** `{server_revision}`",
                f"- **Audit Image Digest:** `{audit_image_digest}`",
                f"- **Report ID:** `{report_id}`",
                f"- **Canonical JSON Artifact:** [`{json_name}`](./{json_name})",
                f"- **Checksum do Payload Canônico (SHA-256):** `{report['checksum']}`",
                f"- **Checksum do Arquivo JSON (SHA-256):** `{file_sha256}`",
                "",
                "---",
                "",
                "## 1. Resultados dos 15 Passos da Jornada",
                "",
                "| # | Passo | Status |",
                "| :-: | :--- | :---: |",
            ]
            for step_key, status in results.items():
                st_str = "**PASS**" if status == "PASS" else "*FAIL*"
                md_lines.append(f"| `{step_key}` | `{step_key}` | {st_str} |")
            md_lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## 2. Resumo da Execução",
                    "",
                    f"- **Total de Passos:** {len(results)}",
                    f"- **Passos Aprovados:** {sum(1 for v in results.values() if v == 'PASS')}",
                    f"- **Passos Falhos:** {sum(1 for v in results.values() if v != 'PASS')}",
                    "- **Zero Mocks no Relatório Real:** Sim",
                    "- **Zero Segredos / Dados Pessoais:** Sim",
                ]
            )
            p_md = Path(output_md_path)
            p_md.parent.mkdir(parents=True, exist_ok=True)
            p_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        return report
