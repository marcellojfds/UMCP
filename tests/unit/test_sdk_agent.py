"""Unit tests for ControlledMemoryAgent."""

import json
from unittest.mock import MagicMock
from omp.sdk.agent import ControlledMemoryAgent
from omp.sdk.cloud import CloudOAuthTransport
from omp.sdk.oauth import OAuthSession, TokenData


def test_controlled_memory_agent_lifecycle() -> None:
    session = OAuthSession("https://staging.test.invalid")
    session.set_tokens(TokenData(access_token="tok123", token_type="Bearer", expires_in=3600, refresh_token="ref123"))

    session.discover_protected_resource = MagicMock(return_value={"resource": "https://staging.test.invalid/mcp"})
    session.discover_authorization_server = MagicMock(return_value={"issuer": "https://staging.test.invalid"})
    session.refresh = MagicMock(return_value=TokenData(access_token="tok_new", token_type="Bearer", expires_in=3600, refresh_token="ref_new"))

    def _mock_revoke(token=None, token_type_hint="access_token"):
        session._tokens = None
        return True

    session.revoke = MagicMock(side_effect=_mock_revoke)

    def _mock_rpc(method, params, retryable=False):
        session.get_valid_access_token()
        return {
            "initialize": {"result": {"protocolVersion": "2025-03-26", "serverInfo": {"name": "umcp-cloud", "version": "1.0"}}},
            "tools/list": {"result": {"tools": [{"name": "memory.write"}, {"name": "memory.search"}, {"name": "memory.update"}, {"name": "memory.forget"}]}},
            "tools/call": {
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({"status": "success", "data": {"record": {"id": "rec-123", "version": 1}}})
                    }]
                }
            },
        }.get(method, {"result": {}})

    transport = CloudOAuthTransport(session)
    transport._rpc = MagicMock(side_effect=_mock_rpc)

    agent = ControlledMemoryAgent(transport)
    report = agent.run_e2e_journey()

    assert report["agent_version"] == "1.0.0"
    assert report["sdk_version"] == "1.0.0"
    assert report["checksum"].startswith("sha256:")
    assert report["summary"]["total_steps"] == 15
    assert report["summary"]["failed_steps"] == 0
    assert report["summary"]["passed_steps"] == 15


