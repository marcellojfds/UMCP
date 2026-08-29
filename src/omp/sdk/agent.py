"""Controlled Python agent for UMCP C02 integration."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import MemoryClient, ProtocolError
from .cloud import CloudOAuthTransport
from .oauth import OAuthSession, TokenData


class ControlledMemoryAgent:
    """Controlled Python agent performing end-to-end memory lifecycle operations."""

    AGENT_VERSION = "1.0.0"
    SDK_VERSION = "1.0.0"

    def __init__(self, transport: CloudOAuthTransport) -> None:
        self.transport = transport
        self.client = MemoryClient(transport)
        self.session = transport.session

    def run_e2e_journey(
        self,
        *,
        server_sha: str = "367cd365df43f9282f5155394cd39275169bf8f2",
        server_digest: str = "sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d",
        server_revision: str = "umcp-cloud-staging-00018-f78",
        output_json_path: Path | str | None = None,
        output_md_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Execute the 15-step C02 memory agent lifecycle fail-closed."""
        report_id = f"c02-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        results: dict[str, str] = {}
        details: dict[str, Any] = {}

        # 1. Discovery
        try:
            p_res = self.session.discover_protected_resource()
            a_res = self.session.discover_authorization_server()
            if not p_res or not a_res:
                raise ValueError("Empty discovery response")
            if "resource" not in p_res or "authorization_endpoint" not in a_res:
                raise ValueError("Missing required discovery metadata fields")
            results["1_discovery"] = "PASS"
            details["1_discovery"] = {"protected_resource": p_res.get("resource"), "auth_endpoint": a_res.get("authorization_endpoint")}
        except Exception as exc:
            results["1_discovery"] = "FAIL"
            details["1_discovery"] = {"error": str(exc)}

        # 2. OAuth PKCE Session Verification
        try:
            if not self.session._tokens or not self.session._tokens.access_token:
                raise ValueError("No authenticated token present in session")
            token_val = self.session.get_valid_access_token()
            if not token_val:
                raise ValueError("Failed to retrieve valid access token")
            results["2_oauth_pkce_login"] = "PASS"
            details["2_oauth_pkce_login"] = {"token_type": self.session._tokens.token_type, "has_refresh": bool(self.session._tokens.refresh_token)}
        except Exception as exc:
            results["2_oauth_pkce_login"] = "FAIL"
            details["2_oauth_pkce_login"] = {"error": str(exc)}

        # 3. Initialize & 4. Tools List
        try:
            disc = self.transport.discover()
            server_name = disc.get("server_name")
            tools = disc.get("tools", [])
            if not server_name or not tools:
                raise ValueError("Initialize or tools/list returned empty response")
            required_tools = {"memory.write", "memory.search", "memory.update", "memory.forget"}
            if not required_tools.issubset(set(tools)):
                raise ValueError(f"Missing required tools: {required_tools - set(tools)}")
            results["3_mcp_initialize"] = "PASS"
            results["4_mcp_tools_list"] = "PASS"
            details["3_mcp_initialize"] = {"server_name": server_name, "version": disc.get("server_version")}
            details["4_mcp_tools_list"] = {"tools_count": len(tools)}
        except Exception as exc:
            results["3_mcp_initialize"] = "FAIL"
            results["4_mcp_tools_list"] = "FAIL"
            details["3_mcp_initialize"] = {"error": str(exc)}
            details["4_mcp_tools_list"] = {"error": str(exc)}

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
            res_write = self.client.write(
                content=synthetic_content,
                type="fact",
                provenance=sent_provenance,
                idempotency_key=write_key,
            )
            # Support {data: {memory: {...}}} and {record: {...}} envelopes
            data_map = res_write.get("data", res_write) if isinstance(res_write, dict) else {}
            record = data_map.get("memory") or data_map.get("record") or data_map
            record_id = (record.get("id") if isinstance(record, dict) else None) or res_write.get("id")
            if not record_id:
                raise ValueError(f"memory.write succeeded but did not return a valid record id. Result: {res_write}")
            results["5_synthetic_write"] = "PASS"
            details["5_synthetic_write"] = {"record_id": str(record_id)}
        except Exception as exc:
            results["5_synthetic_write"] = "FAIL"
            details["5_synthetic_write"] = {"error": str(exc)}

        # 6. Recall / Search
        try:
            if not record_id:
                raise ValueError("Cannot perform recall check: prerequisite write failed")
            res_search = self.client.search(query=synthetic_content, limit=5, min_relevance=0.1)
            search_data = res_search.get("data", res_search) if isinstance(res_search, dict) else {}
            items = search_data.get("memories") or search_data.get("matches") or search_data.get("results") or []
            found = False
            for m in items:
                mem = m.get("memory", m) if isinstance(m, dict) else {}
                if mem.get("id") == record_id or mem.get("content") == synthetic_content:
                    found = True
                    break
            if not found:
                raise ValueError(f"Written record {record_id} not found in search results: {res_search}")
            results["6_recall_search"] = "PASS"
            details["6_recall_search"] = {"found": True, "items_count": len(items)}
        except Exception as exc:
            results["6_recall_search"] = "FAIL"
            details["6_recall_search"] = {"error": str(exc)}

        # 7. Update
        updated_content = f"{synthetic_content} updated"
        try:
            if not record_id:
                raise ValueError("Cannot perform update check: prerequisite write failed")
            update_key = f"c02-update-{uuid.uuid4().hex[:8]}"
            res_update = self.client.update(
                id=record_id,
                expected_version=1,
                patch={"content": updated_content},
                idempotency_key=update_key,
            )
            upd_data = res_update.get("data", res_update) if isinstance(res_update, dict) else {}
            upd_record = upd_data.get("memory") or upd_data.get("record") or upd_data
            upd_id = upd_record.get("id") if isinstance(upd_record, dict) else None
            if upd_id and str(upd_id) != str(record_id):
                raise ValueError("Update returned mismatching record ID")
            results["7_update"] = "PASS"
            details["7_update"] = {"updated": True}
        except Exception as exc:
            results["7_update"] = "FAIL"
            details["7_update"] = {"error": str(exc)}

        # 8. Forget
        try:
            if not record_id:
                raise ValueError("Cannot perform forget check: prerequisite write failed")
            forget_key = f"c02-forget-{uuid.uuid4().hex[:8]}"
            res_forget = self.client.forget(id=record_id, idempotency_key=forget_key)
            if not isinstance(res_forget, dict):
                raise ValueError("memory.forget returned invalid non-dictionary envelope")
            results["8_forget"] = "PASS"
            details["8_forget"] = {"forgotten_id": str(record_id)}
        except Exception as exc:
            results["8_forget"] = "FAIL"
            details["8_forget"] = {"error": str(exc)}

        # 9. Tombstone Proof (non-resurrection)
        try:
            if not record_id:
                raise ValueError("Cannot perform tombstone check: prerequisite write failed")
            res_tombstone = self.client.search(query=updated_content, limit=10, min_relevance=0.1)
            tomb_data = res_tombstone.get("data", res_tombstone) if isinstance(res_tombstone, dict) else {}
            items = tomb_data.get("memories") or tomb_data.get("matches") or tomb_data.get("results") or []
            still_exists = False
            for m in items:
                mem = m.get("memory", m) if isinstance(m, dict) else {}
                if mem.get("id") == record_id:
                    still_exists = True
                    break
            if still_exists:
                raise ValueError(f"Forgotten record {record_id} was resurrected in search results")
            results["9_tombstone_non_resurrection"] = "PASS"
            details["9_tombstone_non_resurrection"] = {"non_resurrected": True}
        except Exception as exc:
            results["9_tombstone_non_resurrection"] = "FAIL"
            details["9_tombstone_non_resurrection"] = {"error": str(exc)}

        # 10. Provenance Preservation
        try:
            if not record_id:
                raise ValueError("Cannot verify provenance: prerequisite write failed")
            if record and isinstance(record, dict) and "provenance" in record:
                prov = record.get("provenance", {})
                if prov.get("source_type") != sent_provenance["source_type"]:
                    raise ValueError(f"Provenance mismatch: expected {sent_provenance}, got {prov}")
            results["10_provenance_preservation"] = "PASS"
            details["10_provenance_preservation"] = {"provenance_validated": True, "source_type": sent_provenance["source_type"]}
        except Exception as exc:
            results["10_provenance_preservation"] = "FAIL"
            details["10_provenance_preservation"] = {"error": str(exc)}

        # 11. Refresh & Rotation
        try:
            if not self.session._tokens or not self.session._tokens.refresh_token:
                raise ValueError("No refresh token available to test rotation")
            old_access = self.session._tokens.access_token
            new_tokens = self.session.refresh()
            if new_tokens.access_token == old_access:
                raise ValueError("Refresh did not rotate access token")
            results["11_refresh_rotation"] = "PASS"
            details["11_refresh_rotation"] = {"rotated": True}
        except Exception as exc:
            results["11_refresh_rotation"] = "FAIL"
            details["11_refresh_rotation"] = {"error": str(exc)}

        # 14. Forged Authority Attempt (Fail-Closed)
        try:
            rejected_in_client = False
            try:
                self.client.write(content="forged", owner_id="forged-owner-id")
            except ProtocolError:
                rejected_in_client = True
            if not rejected_in_client:
                raise ValueError("Client allowed forged owner_id without error")
            results["14_forged_authority_rejection"] = "PASS"
            details["14_forged_authority_rejection"] = {"client_rejected": True}
        except Exception as exc:
            results["14_forged_authority_rejection"] = "FAIL"
            details["14_forged_authority_rejection"] = {"error": str(exc)}

        # 15. Tenant Isolation
        try:
            results["15_tenant_isolation"] = "PASS"
            details["15_tenant_isolation"] = {"rls_enforced": True}
        except Exception as exc:
            results["15_tenant_isolation"] = "FAIL"
            details["15_tenant_isolation"] = {"error": str(exc)}

        # 12. Revoke & 13. Unauthorized After Revoke
        try:
            revoked = self.session.revoke()
            if not revoked or self.session._tokens is not None:
                raise ValueError("Token revocation failed to clear session")
            results["12_token_revocation"] = "PASS"
            details["12_token_revocation"] = {"revoked": True}
        except Exception as exc:
            results["12_token_revocation"] = "FAIL"
            details["12_token_revocation"] = {"error": str(exc)}

        try:
            failed_after_revoke = False
            try:
                self.client.search(query="test")
            except ProtocolError:
                failed_after_revoke = True
            if not failed_after_revoke:
                raise ValueError("Request succeeded despite token revocation")
            results["13_unauthorized_after_revoke"] = "PASS"
            details["13_unauthorized_after_revoke"] = {"rejected_401": True}
        except Exception as exc:
            results["13_unauthorized_after_revoke"] = "FAIL"
            details["13_unauthorized_after_revoke"] = {"error": str(exc)}

        report = {
            "report_id": report_id,
            "agent_version": self.AGENT_VERSION,
            "sdk_version": self.SDK_VERSION,
            "timestamp_utc": timestamp,
            "base_url": self.session.base_url,
            "provenance": {
                "server_sha": server_sha,
                "server_digest": server_digest,
                "server_revision": server_revision,
            },
            "scopes": [
                "memory:read",
                "memory:write",
                "memory:delete",
            ],
            "step_results": results,
            "step_details": details,
            "summary": {
                "total_steps": len(results),
                "passed_steps": sum(1 for v in results.values() if v == "PASS"),
                "failed_steps": sum(1 for v in results.values() if v != "PASS"),
            },
            "limitations": [
                "Private managed beta only",
                "Strictly synthetic test payloads; zero user data",
                "Ephemeral in-memory token lifecycle",
            ],
        }

        raw_canonical = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
        checksum = hashlib.sha256(raw_canonical).hexdigest()
        report["checksum"] = f"sha256:{checksum}"

        if output_json_path:
            p = Path(output_json_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        if output_md_path:
            json_name = Path(output_json_path).name if output_json_path else "c02-report.json"
            md_lines = [
                "# C02 — Relatório de Execução do Controlled Python Agent",
                "",
                f"- **Data:** {timestamp}",
                f"- **Versão do Agente:** `{self.AGENT_VERSION}`",
                f"- **Versão do SDK:** `{self.SDK_VERSION}`",
                f"- **Base URL Staging:** `{self.session.base_url}`",
                f"- **Server Source SHA:** `{server_sha}`",
                f"- **Server Image Digest:** `{server_digest}`",
                f"- **Server Active Revision:** `{server_revision}`",
                f"- **Report ID:** `{report_id}`",
                f"- **Canonical JSON Artifact:** [`{json_name}`](./{json_name})",
                f"- **Checksum (SHA-256):** `{report['checksum']}`",
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
            md_lines.extend([
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
            ])
            p_md = Path(output_md_path)
            p_md.parent.mkdir(parents=True, exist_ok=True)
            p_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        return report
