"""Unit and contract tests for UMCP Cloud SDK."""

import json
from unittest.mock import MagicMock, patch
import pytest

from omp.sdk.client import MemoryClient, ProtocolError
from omp.sdk.cloud import CloudOAuthTransport
from omp.sdk.oauth import (
    OAuthSession,
    TokenData,
    _validate_loopback_redirect_uri,
    generate_pkce_pair,
)
from omp.sdk.runner import ALL_CAPABILITIES, generate_c01_report


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

    # Reject textual localhost
    with pytest.raises(ValueError) as exc:
        _validate_loopback_redirect_uri("http://localhost:8765/callback")
    assert "must be literal 127.0.0.1 or ::1" in str(exc.value)

    # Reject https or non-loopback
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


def test_c01_report_fail_closed_without_results() -> None:
    # Fail-closed: empty transport_results results in ALL capabilities as unverified
    report = generate_c01_report(base_url="https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app")
    assert report["sdk_version"] == "1.0.0"
    assert report["protocol_version"] == "omp.mcp.v0"
    assert report["checksum"].startswith("sha256:")
    assert len(report["matrix"]["supported"]) == 0
    assert len(report["matrix"]["unverified"]) == len(ALL_CAPABILITIES)


def test_c01_report_with_results() -> None:
    results = {cap: "PASS" for cap in ALL_CAPABILITIES}
    report = generate_c01_report(
        base_url="https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app",
        transport_results=results,
    )
    assert len(report["matrix"]["supported"]) == len(ALL_CAPABILITIES)
    assert len(report["matrix"]["unverified"]) == 0
