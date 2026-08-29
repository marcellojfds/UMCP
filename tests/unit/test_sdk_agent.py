"""Unit tests for ControlledMemoryAgent with strict negative failure verification."""

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
import pytest

from omp.sdk.agent import ControlledMemoryAgent
from omp.sdk.cloud import CloudOAuthTransport
from omp.sdk.oauth import OAuthSession, TokenData


def _build_mock_transport(base_url: str, access_token: str, refresh_token: str) -> tuple[OAuthSession, CloudOAuthTransport]:
    session = OAuthSession(base_url)
    session.set_tokens(TokenData(access_token=access_token, token_type="Bearer", expires_in=3600, refresh_token=refresh_token))
    session.discover_protected_resource = MagicMock(return_value={"resource": f"{base_url}/mcp"})
    session.discover_authorization_server = MagicMock(return_value={"issuer": base_url, "authorization_endpoint": f"{base_url}/authorize", "token_endpoint": f"{base_url}/token"})
    session.refresh = MagicMock(return_value=TokenData(access_token=f"{access_token}_new", token_type="Bearer", expires_in=3600, refresh_token=f"{refresh_token}_new"))

    def _mock_revoke(token=None, token_type_hint="access_token"):
        session._tokens = None
        return True

    session.revoke = MagicMock(side_effect=_mock_revoke)

    forgotten_ids = set()

    def _mock_rpc(method, params, retryable=False):
        if method == "initialize":
            return {"result": {"protocolVersion": "2025-03-26", "serverInfo": {"name": "umcp-cloud", "version": "1.0"}}}
        if method == "tools/list":
            return {"result": {"tools": [{"name": "memory.write"}, {"name": "memory.search"}, {"name": "memory.update"}, {"name": "memory.forget"}]}}
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "memory.write":
                prov = args.get("provenance", {"source_type": "user", "captured_at": "2026-08-29T00:00:00Z", "source_id": "c02-test-actor"})
                rec_id = "rec-b-456" if access_token == "tok_b" else "rec-123"
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": rec_id, "version": 1, "provenance": prov}}})}]}}
            if name == "memory.search":
                q = args.get("query", "")
                if access_token == "tok_a":
                    if "tenant_b_isolated_secret" in q or "rec-123" in forgotten_ids:
                        matches = []
                    else:
                        matches = [{"memory": {"id": "rec-123", "content": q}}]
                elif access_token == "tok_b":
                    if "tenant_b_isolated_secret" in q:
                        matches = [{"memory": {"id": "rec-b-456", "content": q}}]
                    else:
                        matches = []
                else:
                    matches = []
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memories": matches}})}]}}
            if name == "memory.update":
                target_id = args.get("id")
                if (access_token == "tok_a" and target_id == "rec-b-456") or (access_token == "tok_b" and target_id == "rec-123"):
                    raise ValueError("Cross-tenant record not found")
                content = args.get("patch", {}).get("content", "updated")
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": target_id or "rec-123", "version": 2, "content": content}}})}]}}
            if name == "memory.forget":
                forgotten_ids.add(args.get("id"))
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"id": args.get("id"), "status": "forgotten"}})}]}}
        return {"result": {}}

    transport = CloudOAuthTransport(session)
    transport._rpc = MagicMock(side_effect=_mock_rpc)
    return session, transport


def test_controlled_memory_agent_15_steps_success() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),  # Forged probe
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None), # Old refresh probe
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),  # Revoke probe
        ]
        report = agent.run_e2e_journey(
            server_sha="367cd365df43f9282f5155394cd39275169bf8f2",
            server_digest="sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d",
            server_revision="umcp-cloud-staging-00018-f78",
        )

    assert report["agent_version"] == "1.0.0"
    assert report["sdk_version"] == "1.0.0"
    assert report["checksum"].startswith("sha256:")
    assert report["file_sha256"].startswith("sha256:")
    assert report["summary"]["total_steps"] == 15
    assert report["summary"]["passed_steps"] == 15
    assert report["summary"]["failed_steps"] == 0
    assert report["step_results"]["15_tenant_isolation"] == "PASS"


def test_forged_authority_fails_when_server_does_not_reject() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    mock_resp_200 = MagicMock()
    mock_resp_200.__enter__.return_value.read.return_value = json.dumps({"result": {"content": [{"type": "text", "text": "accepted"}]}}).encode("utf-8")

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            mock_resp_200,  # Server accepted forged authority!
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey(server_sha="sha", server_digest="dig", server_revision="rev")

    assert report["step_results"]["14_forged_authority_rejection"] == "FAIL"
    assert "Server did not reject forged authority" in report["step_details"]["14_forged_authority_rejection"]["error"]


def test_tenant_isolation_fails_without_second_tenant() -> None:
    _, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    agent = ControlledMemoryAgent(transport_a, transport_b=None)

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey(server_sha="sha", server_digest="dig", server_revision="rev")

    assert report["step_results"]["15_tenant_isolation"] == "FAIL"
    assert "Only one tenant/identity provided" in report["step_details"]["15_tenant_isolation"]["error"]


def test_provenance_fails_when_missing_or_mismatching() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    original_rpc = transport_a._rpc.side_effect

    def _corrupted_write(method, params, retryable=False):
        if method == "tools/call" and params.get("name") == "memory.write":
            return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": "rec-123", "version": 1, "provenance": {"source_type": "wrong"}}}}) }]}}
        return original_rpc(method, params, retryable)

    transport_a._rpc = MagicMock(side_effect=_corrupted_write)
    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey(server_sha="sha", server_digest="dig", server_revision="rev")

    assert report["step_results"]["10_provenance_preservation"] == "FAIL"
    assert "Provenance source_type mismatch" in report["step_details"]["10_provenance_preservation"]["error"]


def test_update_fails_without_version_increment() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    original_rpc = transport_a._rpc.side_effect

    def _unincremented_update(method, params, retryable=False):
        if method == "tools/call" and params.get("name") == "memory.update":
            content = params.get("arguments", {}).get("patch", {}).get("content", "updated")
            return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": "rec-123", "version": 1, "content": content}}})}]}}
        return original_rpc(method, params, retryable)

    transport_a._rpc = MagicMock(side_effect=_unincremented_update)
    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey(server_sha="sha", server_digest="dig", server_revision="rev")

    assert report["step_results"]["7_update"] == "FAIL"
    assert "Update expected incremented version 2" in report["step_details"]["7_update"]["error"]


def test_forget_fails_without_tombstone_status() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    original_rpc = transport_a._rpc.side_effect

    def _corrupted_forget(method, params, retryable=False):
        if method == "tools/call" and params.get("name") == "memory.forget":
            return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"id": "rec-123", "status": "unknown"}})}]}}
        return original_rpc(method, params, retryable)

    transport_a._rpc = MagicMock(side_effect=_corrupted_forget)
    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey(server_sha="sha", server_digest="dig", server_revision="rev")

    assert report["step_results"]["8_forget"] == "FAIL"
    assert "Forget did not return explicit tombstone status" in report["step_details"]["8_forget"]["error"]
