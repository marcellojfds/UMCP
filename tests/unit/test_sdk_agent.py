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
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": "rec-123", "version": 1, "provenance": prov}}})}]}}
            if name == "memory.search":
                q = args.get("query", "")
                if "isolated_secret" in q and access_token == "tok_a":
                    # Cross-tenant zero leakage
                    matches = []
                elif "rec-123" in forgotten_ids:
                    matches = []
                else:
                    matches = [{"memory": {"id": "rec-123", "content": q}}]
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memories": matches}})}]}}
            if name == "memory.update":
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": "rec-123", "version": 2}}})}]}}
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
        # Mock HTTP responses: forged raw probe -> old refresh probe -> revoke 401 probe
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey()

    assert report["agent_version"] == "1.0.0"
    assert report["sdk_version"] == "1.0.0"
    assert report["checksum"].startswith("sha256:")
    assert report["file_sha256"].startswith("sha256:")
    assert report["summary"]["total_steps"] == 15
    assert report["summary"]["passed_steps"] == 15
    assert report["summary"]["failed_steps"] == 0
    assert report["step_results"]["15_tenant_isolation"] == "PASS"


def test_tenant_isolation_fails_without_second_tenant() -> None:
    _, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    agent = ControlledMemoryAgent(transport_a, transport_b=None)

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey()

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
        report = agent.run_e2e_journey()

    assert report["step_results"]["10_provenance_preservation"] == "FAIL"
    assert "Provenance source_type mismatch" in report["step_details"]["10_provenance_preservation"]["error"]


def test_update_fails_without_version_increment() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    original_rpc = transport_a._rpc.side_effect

    def _unincremented_update(method, params, retryable=False):
        if method == "tools/call" and params.get("name") == "memory.update":
            return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": "rec-123", "version": 1}}})}]}}
        return original_rpc(method, params, retryable)

    transport_a._rpc = MagicMock(side_effect=_unincremented_update)
    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None),
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),
        ]
        report = agent.run_e2e_journey()

    assert report["step_results"]["7_update"] == "FAIL"
    assert "Update expected version 2" in report["step_details"]["7_update"]["error"]


def test_refresh_fails_when_old_token_not_rejected() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    mock_resp_200 = MagicMock()
    mock_resp_200.status = 200

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),  # Forged probe
            mock_resp_200,  # Old refresh unexpectedly succeeded with 200
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None), # Revoke probe
        ]
        report = agent.run_e2e_journey()

    assert report["step_results"]["11_refresh_rotation"] == "FAIL"
    assert "Old refresh token was not rejected with HTTP 400" in report["step_details"]["11_refresh_rotation"]["error"]


def test_revoke_fails_when_post_revoke_is_not_401() -> None:
    session_a, transport_a = _build_mock_transport("https://staging.test.invalid", "tok_a", "ref_a")
    session_b, transport_b = _build_mock_transport("https://staging.test.invalid", "tok_b", "ref_b")

    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)

    mock_resp_200 = MagicMock()
    mock_resp_200.status = 200

    with patch("omp.sdk.agent.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),  # Forged probe
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None), # Old refresh probe
            mock_resp_200,  # Post-revoke probe returned 200 instead of 401
        ]
        report = agent.run_e2e_journey()

    assert report["step_results"]["13_unauthorized_after_revoke"] == "FAIL"
    assert "Revoked access token was not rejected by server with HTTP 401" in report["step_details"]["13_unauthorized_after_revoke"]["error"]
