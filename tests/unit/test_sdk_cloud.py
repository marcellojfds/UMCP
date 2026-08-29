"""Unit and contract tests for UMCP Cloud SDK."""

import json
from unittest.mock import MagicMock, patch
import pytest

from omp.sdk.client import MemoryClient, ProtocolError
from omp.sdk.cloud import CloudOAuthTransport
from omp.sdk.oauth import OAuthSession, TokenData, generate_pkce_pair
from omp.sdk.runner import generate_c01_report


def test_pkce_pair_generation() -> None:
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) >= 43
    assert len(challenge) >= 43
    assert "/" not in verifier and "+" not in verifier
    assert "/" not in challenge and "+" not in challenge


def test_oauth_session_auth_url() -> None:
    session = OAuthSession("https://staging.test.invalid", client_id="test-client", redirect_uri="https://staging.test.invalid/cb")
    url = session.get_authorization_url(state="xyz123", code_challenge="chal123")
    assert url.startswith("https://staging.test.invalid/authorize?")
    assert "client_id=test-client" in url
    assert "code_challenge=chal123" in url
    assert "code_challenge_method=S256" in url
    assert "state=xyz123" in url


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


def test_c01_report_generation() -> None:
    report = generate_c01_report(base_url="https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app")
    assert report["sdk_version"] == "1.0.0"
    assert report["protocol_version"] == "omp.mcp.v0"
    assert report["checksum"].startswith("sha256:")
    assert "supported" in report["matrix"]
    assert "experimental" in report["matrix"]
    assert "unverified" in report["matrix"]
    assert len(report["matrix"]["supported"]) >= 10
