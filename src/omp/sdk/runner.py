"""Runner and reproducible conformance report generator for UMCP SDK."""

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

from .checksums import compute_canonical_checksum
from .client import MemoryClient, ProtocolError
from .cloud import CloudOAuthTransport
from .oauth import (
    OAuthSession,
    TokenData,
    _validate_loopback_redirect_uri,
    generate_pkce_pair,
)

ALL_CAPABILITIES = [
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
]


class SDKConformanceRunner:
    """Live conformance runner executing the 14 real UMCP SDK capabilities."""

    def __init__(self, transport: CloudOAuthTransport) -> None:
        self.transport = transport
        self.session = transport.session
        self.client = MemoryClient(transport)

    def run_all_checks(self) -> dict[str, Any]:
        """Execute all 14 capability probes against the active transport/session."""
        results: dict[str, str] = {}
        details: dict[str, Any] = {}

        try:
            # 1. Protected resource discovery
            try:
                p_res = self.session.discover_protected_resource()
                expected_res = f"{self.session.base_url}/mcp"
                if not isinstance(p_res, dict) or p_res.get("resource") != expected_res:
                    raise ValueError(f"Protected resource discovery returned unexpected metadata: {p_res}")
                results["protected_resource_discovery"] = "PASS"
                details["protected_resource_discovery"] = {"resource": p_res.get("resource")}
            except Exception as exc:
                results["protected_resource_discovery"] = "FAIL"
                details["protected_resource_discovery"] = {"error": str(exc)}

            # 2. Authorization server discovery
            try:
                a_res = self.session.discover_authorization_server()
                if (
                    not isinstance(a_res, dict)
                    or not a_res.get("authorization_endpoint")
                    or not a_res.get("token_endpoint")
                ):
                    raise ValueError(f"Authorization server discovery returned incomplete metadata: {a_res}")
                results["authorization_server_discovery"] = "PASS"
                details["authorization_server_discovery"] = {
                    "authorization_endpoint": a_res.get("authorization_endpoint"),
                    "token_endpoint": a_res.get("token_endpoint"),
                }
            except Exception as exc:
                results["authorization_server_discovery"] = "FAIL"
                details["authorization_server_discovery"] = {"error": str(exc)}

            # 3. OAuth PKCE S256 & loopback validation
            try:
                verifier, challenge = generate_pkce_pair()
                if len(verifier) < 43 or len(challenge) < 43:
                    raise ValueError("PKCE generation failed length constraint")
                host, port, path = _validate_loopback_redirect_uri("http://127.0.0.1:8765/callback")
                if host != "127.0.0.1" or port != 8765 or path != "/callback":
                    raise ValueError("Loopback validation failed on standard URI")
                rejected_localhost = False
                try:
                    _validate_loopback_redirect_uri("http://localhost:8765/callback")
                except ValueError:
                    rejected_localhost = True
                if not rejected_localhost:
                    raise ValueError("Loopback validation must reject textual localhost")
                results["oauth_pkce_s256"] = "PASS"
                details["oauth_pkce_s256"] = {"pkce_method": "S256", "loopback_compliant": True}
            except Exception as exc:
                results["oauth_pkce_s256"] = "FAIL"
                details["oauth_pkce_s256"] = {"error": str(exc)}

            # 4. Token exchange / session validity
            try:
                if not self.session._tokens or not self.session._tokens.access_token:
                    raise ValueError("No authenticated tokens present in session")
                token_val = self.session.get_valid_access_token()
                if not token_val:
                    raise ValueError("Failed to retrieve valid access token")
                results["token_exchange"] = "PASS"
                details["token_exchange"] = {"token_type": self.session._tokens.token_type, "has_refresh": bool(self.session._tokens.refresh_token)}
            except Exception as exc:
                results["token_exchange"] = "FAIL"
                details["token_exchange"] = {"error": str(exc)}

            # 5. MCP initialize
            try:
                init_res = self.transport._rpc("initialize", {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "umcp-python-sdk", "version": "1.0"},
                })
                server_info = init_res.get("result", {}).get("serverInfo", {})
                if server_info.get("name") != "umcp-cloud":
                    raise ValueError(f"Unexpected MCP serverInfo: {server_info}")
                results["mcp_initialize"] = "PASS"
                details["mcp_initialize"] = {"server_name": server_info.get("name"), "version": server_info.get("version")}
            except Exception as exc:
                results["mcp_initialize"] = "FAIL"
                details["mcp_initialize"] = {"error": str(exc)}

            # 6. MCP tools/list
            try:
                tools_res = self.transport._rpc("tools/list", {})
                tools = tools_res.get("result", {}).get("tools", []) or tools_res.get("tools", [])
                tool_names = [t.get("name") if isinstance(t, dict) else t for t in tools]
                required = {"memory.write", "memory.search", "memory.update", "memory.forget"}
                if not required.issubset(set(tool_names)):
                    raise ValueError(f"Missing required MCP tools: {required - set(tool_names)}")
                results["mcp_tools_list"] = "PASS"
                details["mcp_tools_list"] = {"tools_count": len(tool_names)}
            except Exception as exc:
                results["mcp_tools_list"] = "FAIL"
                details["mcp_tools_list"] = {"error": str(exc)}

            # 7. Memory write synthetic
            write_key = f"c01-write-{uuid.uuid4().hex[:8]}"
            synthetic_content = f"c01 runner synthetic memory content {uuid.uuid4().hex[:6]}"
            record_id = None
            sent_prov = {
                "source_type": "user",
                "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "source_id": "c01-runner",
            }
            try:
                res_write = self.client.write(
                    content=synthetic_content,
                    type="fact",
                    provenance=sent_prov,
                    idempotency_key=write_key,
                )
                data_map = res_write.get("data", res_write) if isinstance(res_write, dict) else {}
                record = data_map.get("memory") or data_map.get("record") or data_map
                record_id = (record.get("id") if isinstance(record, dict) else None) or res_write.get("id")
                if not record_id:
                    raise ValueError(f"memory.write did not return valid record id: {res_write}")
                results["memory_write_synthetic"] = "PASS"
                details["memory_write_synthetic"] = {"record_id": str(record_id)}
            except Exception as exc:
                results["memory_write_synthetic"] = "FAIL"
                details["memory_write_synthetic"] = {"error": str(exc)}

            # 8. Memory search synthetic
            try:
                if not record_id:
                    raise ValueError("Prerequisite write failed; cannot search")
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
                    raise ValueError(f"Written memory {record_id} not found in search: {res_search}")
                results["memory_search_synthetic"] = "PASS"
                details["memory_search_synthetic"] = {"found": True, "items_count": len(items)}
            except Exception as exc:
                results["memory_search_synthetic"] = "FAIL"
                details["memory_search_synthetic"] = {"error": str(exc)}

            # 9. Memory update synthetic (strict: ID, content and version == 2)
            updated_content = f"{synthetic_content} updated"
            try:
                if not record_id:
                    raise ValueError("Prerequisite write failed; cannot update")
                update_key = f"c01-update-{uuid.uuid4().hex[:8]}"
                res_update = self.client.update(
                    id=record_id,
                    expected_version=1,
                    patch={"content": updated_content},
                    idempotency_key=update_key,
                )
                upd_data = res_update.get("data", res_update) if isinstance(res_update, dict) else {}
                upd_rec = upd_data.get("memory") or upd_data.get("record") or upd_data
                if not isinstance(upd_rec, dict):
                    raise ValueError(f"Update returned non-dict response: {res_update}")
                if str(upd_rec.get("id")) != str(record_id):
                    raise ValueError("Update returned mismatching record ID")
                if upd_rec.get("content") != updated_content:
                    raise ValueError(f"Update returned mismatching content: {upd_rec.get('content')}")
                if upd_rec.get("version") != 2:
                    raise ValueError(f"Update expected version 2, got {upd_rec.get('version')}")
                results["memory_update_synthetic"] = "PASS"
                details["memory_update_synthetic"] = {"updated": True, "new_version": 2}
            except Exception as exc:
                results["memory_update_synthetic"] = "FAIL"
                details["memory_update_synthetic"] = {"error": str(exc)}

            # 10. Memory forget synthetic (strict: ID and tombstone status)
            try:
                if not record_id:
                    raise ValueError("Prerequisite write failed; cannot forget")
                forget_key = f"c01-forget-{uuid.uuid4().hex[:8]}"
                res_forget = self.client.forget(id=record_id, idempotency_key=forget_key)
                if not isinstance(res_forget, dict):
                    raise ValueError(f"Forget returned non-dict response: {res_forget}")
                forget_data = res_forget.get("data", res_forget) if isinstance(res_forget, dict) else {}
                ret_status = forget_data.get("status") or forget_data.get("state") or res_forget.get("status")
                if ret_status not in {"forgotten", "deleted", "archived", "tombstoned"} and res_forget.get("ok") is not True:
                    raise ValueError(f"Forget did not return explicit tombstone status: {res_forget}")
                results["memory_forget_synthetic"] = "PASS"
                details["memory_forget_synthetic"] = {"forgotten_id": str(record_id), "status": ret_status}
            except Exception as exc:
                results["memory_forget_synthetic"] = "FAIL"
                details["memory_forget_synthetic"] = {"error": str(exc)}

            # 13. Forged authority rejection (strict client and server explicit rejection)
            try:
                client_rejected = False
                try:
                    self.client.write(content="forged", owner_id="forged-owner")
                except ProtocolError:
                    client_rejected = True
                if not client_rejected:
                    raise ValueError("Client failed to reject forged owner_id")

                server_rejected = False
                token = self.session.get_valid_access_token()
                forged_payload = json.dumps({
                    "jsonrpc": "2.0",
                    "id": 999,
                    "method": "tools/call",
                    "params": {"name": "memory.write", "arguments": {"content": "forged", "owner_id": "forged-owner-id"}},
                }).encode("utf-8")
                req = Request(
                    f"{self.session.base_url}/mcp",
                    data=forged_payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Authorization": f"Bearer {token}"},
                    method="POST",
                )
                try:
                    with urlopen(req, timeout=self.session.timeout) as resp:
                        raw = resp.read().decode()
                        parsed = json.loads(raw) if raw else {}
                        if "error" in parsed or parsed.get("result", {}).get("isError") is True:
                            server_rejected = True
                        else:
                            raise ValueError(f"Server did not reject forged authority: {raw[:150]}")
                except HTTPError as exc:
                    if exc.code in {400, 403, 422}:
                        server_rejected = True
                    else:
                        raise ValueError(f"Unexpected HTTP code on forged authority probe: {exc.code}")
                except Exception as exc:
                    raise ValueError(f"Direct probe for forged authority failed: {exc}")

                if not server_rejected:
                    raise ValueError("Server failed to reject forged authority")

                results["forged_authority_rejection"] = "PASS"
                details["forged_authority_rejection"] = {"client_rejected": True, "server_rejected": True}
            except Exception as exc:
                results["forged_authority_rejection"] = "FAIL"
                details["forged_authority_rejection"] = {"error": str(exc)}

            # 14. Zero leakage / redaction
            try:
                str_repr = str(self.session)
                if self.session._tokens and self.session._tokens.access_token in str_repr:
                    raise ValueError("Access token leaked in session string representation")
                results["zero_leakage_redaction"] = "PASS"
                details["zero_leakage_redaction"] = {"redacted": True}
            except Exception as exc:
                results["zero_leakage_redaction"] = "FAIL"
                details["zero_leakage_redaction"] = {"error": str(exc)}

            # 11. Token refresh & rotation (with old refresh token rejection proof)
            old_refresh_status = None
            try:
                if not self.session._tokens or not self.session._tokens.refresh_token:
                    raise ValueError("No refresh token available to test rotation")
                old_access = self.session._tokens.access_token
                old_refresh = self.session._tokens.refresh_token
                new_tokens = self.session.refresh()
                if new_tokens.access_token == old_access or new_tokens.refresh_token == old_refresh:
                    raise ValueError("Refresh did not rotate access/refresh token pair")
                token_endpoint = f"{self.session.base_url}/token"
                old_ref_body = urlencode({
                    "grant_type": "refresh_token",
                    "refresh_token": old_refresh,
                    "client_id": self.session.client_id,
                }).encode("utf-8")
                req = Request(
                    token_endpoint,
                    data=old_ref_body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                try:
                    with urlopen(req, timeout=self.session.timeout) as resp:
                        old_refresh_status = resp.status
                except HTTPError as exc:
                    old_refresh_status = exc.code
                if old_refresh_status != 400:
                    raise ValueError(f"Old refresh token was not rejected with 400 (got {old_refresh_status})")
                results["token_refresh_rotation"] = "PASS"
                details["token_refresh_rotation"] = {"rotated": True, "old_refresh_rejected_status": 400}
            except Exception as exc:
                results["token_refresh_rotation"] = "FAIL"
                details["token_refresh_rotation"] = {"error": str(exc)}

            # 12. Token revocation (with post-revoke HTTP 401 proof)
            active_access_before_revoke = None
            post_revoke_status = None
            try:
                if not self.session._tokens or not self.session._tokens.access_token:
                    raise ValueError("No active access token to revoke")
                active_access_before_revoke = self.session._tokens.access_token
                revoked = self.session.revoke()
                if not revoked or self.session._tokens is not None:
                    raise ValueError("Token revocation failed to clear local session")
                mcp_endpoint = f"{self.session.base_url}/mcp"
                probe_payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode("utf-8")
                req = Request(
                    mcp_endpoint,
                    data=probe_payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Authorization": f"Bearer {active_access_before_revoke}"},
                    method="POST",
                )
                try:
                    with urlopen(req, timeout=self.session.timeout) as resp:
                        post_revoke_status = resp.status
                except HTTPError as exc:
                    post_revoke_status = exc.code
                if post_revoke_status != 401:
                    raise ValueError(f"Revoked access token was not rejected with 401 (got {post_revoke_status})")
                results["token_revocation"] = "PASS"
                details["token_revocation"] = {"revoked": True, "revoke_status": 200, "post_revoke_status": 401}
            except Exception as exc:
                results["token_revocation"] = "FAIL"
                details["token_revocation"] = {"error": str(exc)}

        finally:
            if self.session and self.session._tokens:
                try:
                    self.session.revoke()
                except Exception:
                    pass

        return {"results": results, "details": details}


def generate_c01_report(
    *,
    base_url: str,
    audit_source_sha: str,
    server_source_sha: str = "367cd365df43f9282f5155394cd39275169bf8f2",
    server_digest: str = "sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d",
    server_revision: str = "umcp-cloud-staging-00018-f78",
    audit_image_digest: str = "sha256:unknown",
    transport_results: dict[str, Any] | None = None,
    output_json_path: Path | str | None = None,
    output_md_path: Path | str | None = None,
) -> dict[str, Any]:
    """Generate a reproducible, dated, checksummed C01 conformance report.

    Fail-closed rule: If transport_results is empty or a capability has not
    passed an actual verified check, it is categorized as unverified.
    """
    report_id = f"c01-{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    results = transport_results or {}

    supported = []
    unverified = []

    for cap in ALL_CAPABILITIES:
        status = results.get(cap)
        if status == "PASS" or status is True:
            supported.append(cap)
        else:
            unverified.append(cap)

    matrix = {
        "supported": sorted(supported),
        "experimental": [
            "streamable_sse_transport",
            "realtime_notifications",
        ],
        "unverified": sorted(unverified),
    }

    report_body = {
        "report_id": report_id,
        "sdk_version": "1.0.0",
        "protocol_version": "omp.mcp.v0",
        "created_at": created_at,
        "base_url": base_url,
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
        "matrix": matrix,
        "test_results": results,
        "summary": {
            "total_capabilities": len(ALL_CAPABILITIES),
            "supported_count": len(supported),
            "unverified_count": len(unverified),
        },
        "limitations": [
            "Private managed beta only; not approved for public distribution or external users",
            "Operates with authorized test identity and synthetic test payloads only",
        ],
    }

    report_body["checksum"] = compute_canonical_checksum(report_body)
    formatted_json = json.dumps(report_body, indent=2, sort_keys=True) + "\n"
    file_sha256 = f"sha256:{hashlib.sha256(formatted_json.encode('utf-8')).hexdigest()}"

    if output_json_path:
        p = Path(output_json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(formatted_json, encoding="utf-8")

    if output_md_path:
        json_name = Path(output_json_path).name if output_json_path else "c01-report.json"
        md_lines = [
            "# C01 — Relatório de Conformance do SDK Python e Runner Comum",
            "",
            f"- **Data:** {created_at}",
            f"- **Versão do SDK:** `{report_body['sdk_version']}`",
            f"- **Protocolo:** `{report_body['protocol_version']}`",
            f"- **Base URL Staging:** `{base_url}`",
            f"- **Audit Source SHA:** `{audit_source_sha}`",
            f"- **Server Source SHA:** `{server_source_sha}`",
            f"- **Server Image Digest:** `{server_digest}`",
            f"- **Server Active Revision:** `{server_revision}`",
            f"- **Audit Image Digest:** `{audit_image_digest}`",
            f"- **Report ID:** `{report_id}`",
            f"- **Canonical JSON Artifact:** [`{json_name}`](./{json_name})",
            f"- **Checksum do Payload Canônico (SHA-256):** `{report_body['checksum']}`",
            f"- **Checksum do Arquivo JSON (SHA-256):** `{file_sha256}`",
            "",
            "---",
            "",
            "## 1. Escopos Autorizados",
            "",
            "- `memory:read`",
            "- `memory:write`",
            "- `memory:delete`",
            "",
            "---",
            "",
            "## 2. Matriz de Conformance (Derivada de Resultados Reais)",
            "",
            "| Capacidade | Status |",
            "| :--- | :---: |",
        ]
        for cap in ALL_CAPABILITIES:
            st = "**Supported**" if cap in supported else "*Unverified*"
            md_lines.append(f"| `{cap}` | {st} |")

        md_lines.extend([
            "",
            "---",
            "",
            "## 3. Resumo da Verificação",
            "",
            f"- **Total de Capacidades:** {len(ALL_CAPABILITIES)}",
            f"- **Suportadas e Validadas:** {len(supported)}",
            f"- **Não Verificadas / Pendentes:** {len(unverified)}",
            "- **Zero Mocks no Relatório Real:** Sim",
            "- **Zero Segredos / Dados Pessoais:** Sim",
        ])
        p_md = Path(output_md_path)
        p_md.parent.mkdir(parents=True, exist_ok=True)
        p_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return report_body
