"""Unit and contract tests for UMCP Cloud SDK and Conformance Runner."""

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
import pytest

from omp.sdk.client import MemoryClient, ProtocolError
from omp.sdk.cloud import CloudOAuthTransport
from omp.sdk.oauth import (
    OAuthSession,
    TokenData,
    _validate_loopback_redirect_uri,
    generate_pkce_pair,
)
from omp.sdk.runner import ALL_CAPABILITIES, SDKConformanceRunner, generate_c01_report


def test_pkce_pair_generation() -> None:
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) >= 43
    assert len(challenge) >= 43
    assert "/" not in verifier and "+" not in verifier
    assert "/" not in challenge and "+" not in challenge


def test_oauth_session_auth_url() -> None:
    session = OAuthSession(
        "https://staging.test.invalid",
        client_id="umcp-python-sdk",
        redirect_uri="http://127.0.0.1:8765/callback",
    )
    url = session.get_authorization_url(state="xyz123", code_challenge="chal123")
    assert url.startswith("https://staging.test.invalid/authorize?")
    assert "client_id=umcp-python-sdk" in url
    assert "code_challenge=chal123" in url
    assert "code_challenge_method=S256" in url
    assert "state=xyz123" in url
    assert "scope=memory%3Aread+memory%3Awrite+memory%3Adelete" in url


def test_invalid_scopes_rejected() -> None:
    session = OAuthSession("https://staging.test.invalid")
    with pytest.raises(ValueError) as exc:
        session.get_authorization_url(
            state="xyz",
            code_challenge="chal",
            scopes=["memory:read", "invalid:scope"],
        )
    assert "is not supported" in str(exc.value)


def test_loopback_redirect_uri_validation() -> None:
    host, port, path = _validate_loopback_redirect_uri("http://127.0.0.1:8765/callback")
    assert host == "127.0.0.1" and port == 8765 and path == "/callback"

    host, port, path = _validate_loopback_redirect_uri("http://[::1]:9000/auth")
    assert host == "::1" and port == 9000 and path == "/auth"

    with pytest.raises(ValueError) as exc:
        _validate_loopback_redirect_uri("http://localhost:8765/callback")
    assert "must be literal 127.0.0.1 or ::1" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        _validate_loopback_redirect_uri("https://example.com/callback")
    assert "must use http://" in str(exc.value)


def test_cloud_transport_rejects_forged_owner_or_tenant() -> None:
    session = OAuthSession("https://staging.test.invalid")
    session.set_tokens(TokenData(access_token="tok123", token_type="Bearer", expires_in=3600))
    transport = CloudOAuthTransport(session)
    client = MemoryClient(transport)

    with pytest.raises(ProtocolError) as exc:
        client.write(content="test", owner_id="forged-owner")
    assert "client must not specify owner_id or tenant_id" in str(exc.value)

    with pytest.raises(ProtocolError) as exc:
        client.search(query="test", tenant_id="forged-tenant")
    assert "client must not specify owner_id or tenant_id" in str(exc.value)


def test_c01_conformance_runner_live_probes_success() -> None:
    session = OAuthSession("https://staging.test.invalid")
    session.set_tokens(TokenData(access_token="tok123", token_type="Bearer", expires_in=3600, refresh_token="ref123"))
    session.discover_protected_resource = MagicMock(return_value={"resource": "https://staging.test.invalid/mcp"})
    session.discover_authorization_server = MagicMock(return_value={"issuer": "https://staging.test.invalid", "authorization_endpoint": "https://staging.test.invalid/authorize", "token_endpoint": "https://staging.test.invalid/token"})
    session.refresh = MagicMock(return_value=TokenData(access_token="tok_new", token_type="Bearer", expires_in=3600, refresh_token="ref_new"))

    def _mock_revoke(token=None, token_type_hint="access_token"):
        session._tokens = None
        return True

    session.revoke = MagicMock(side_effect=_mock_revoke)

    def _mock_rpc(method, params, retryable=False):
        if method == "initialize":
            return {"result": {"protocolVersion": "2025-03-26", "serverInfo": {"name": "umcp-cloud", "version": "1.0"}}}
        if method == "tools/list":
            return {"result": {"tools": [{"name": "memory.write"}, {"name": "memory.search"}, {"name": "memory.update"}, {"name": "memory.forget"}]}}
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "memory.write":
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": "rec-123", "version": 1}}})}]}}
            if name == "memory.search":
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memories": [{"memory": {"id": "rec-123", "content": args.get("query")}}]}})}]}}
            if name == "memory.update":
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"memory": {"id": "rec-123", "version": 2}}})}]}}
            if name == "memory.forget":
                return {"result": {"content": [{"type": "text", "text": json.dumps({"status": "success", "data": {"id": args.get("id"), "status": "forgotten"}})}]}}
        return {"result": {}}

    transport = CloudOAuthTransport(session)
    transport._rpc = MagicMock(side_effect=_mock_rpc)

    runner = SDKConformanceRunner(transport)
    with patch("omp.sdk.runner.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            HTTPError("https://staging.test.invalid/mcp", 400, "Bad Request", {}, None),  # Forged raw probe
            HTTPError("https://staging.test.invalid/token", 400, "Bad Request", {}, None), # Old refresh probe
            HTTPError("https://staging.test.invalid/mcp", 401, "Unauthorized", {}, None),  # Revoke 401 probe
        ]
        checks = runner.run_all_checks()

    assert all(status == "PASS" for status in checks["results"].values())
    report = generate_c01_report(
        base_url="https://staging.test.invalid",
        transport_results=checks["results"],
    )
    assert report["summary"]["supported_count"] == 14
    assert report["summary"]["unverified_count"] == 0
    assert report["checksum"].startswith("sha256:")
    assert report["file_sha256"].startswith("sha256:")


def test_c01_report_fail_closed_without_results() -> None:
    report = generate_c01_report(base_url="https://staging.test.invalid")
    assert report["sdk_version"] == "1.0.0"
    assert report["protocol_version"] == "omp.mcp.v0"
    assert report["checksum"].startswith("sha256:")
    assert len(report["matrix"]["supported"]) == 0
    assert len(report["matrix"]["unverified"]) == len(ALL_CAPABILITIES)
