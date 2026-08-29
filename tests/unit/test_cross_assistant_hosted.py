from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from examples.e2e_cross_assistant_hosted import run_cross_assistant_demo


def test_run_cross_assistant_demo_flow() -> None:
    def _mock_rpc(method, params, retryable=False):
        if method == "initialize":
            return {"result": {"serverInfo": {"name": "umcp-cloud"}}}
        if method == "tools/list":
            return {"result": {"tools": [{"name": "memory.write"}, {"name": "memory.search"}, {"name": "memory.update"}, {"name": "memory.forget"}]}}
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "memory.write":
                return {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"status": "success", "data": {"memory": {"id": "mem_cross_123", "version": 1}}}),
                            }
                        ]
                    }
                }
            if name == "memory.search":
                return {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "status": "success",
                                        "data": {
                                            "memories": [
                                                {
                                                    "memory": {
                                                        "id": "mem_cross_123",
                                                        "content": "User preference: Adopt Clean Architecture and fail-closed security invariants with Python 3.11+.",
                                                    }
                                                }
                                            ]
                                        },
                                    }
                                ),
                            }
                        ]
                    }
                }
            if name == "memory.update":
                return {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"status": "success", "data": {"memory": {"id": "mem_cross_123", "version": 2}}}),
                            }
                        ]
                    }
                }
            if name == "memory.forget":
                return {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"status": "success", "data": {"id": "mem_cross_123", "status": "forgotten"}}),
                            }
                        ]
                    }
                }
        return {"result": {}}

    with patch("omp.sdk.cloud.CloudOAuthTransport._rpc", side_effect=_mock_rpc):
        result = run_cross_assistant_demo(
            base_url="https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app",
            access_token="test_token",
        )

    assert result["status"] == "SUCCESS"
    assert result["cross_assistant_verified"] is True
    assert result["steps"]["1_chatgpt_write"]["status"] == "PASS"
    assert result["steps"]["2_gemini_recall"]["status"] == "PASS"
    assert result["steps"]["3_gemini_update"]["status"] == "PASS"
    assert result["steps"]["4_chatgpt_verify_update"]["status"] == "PASS"
    assert result["steps"]["5_forget"]["status"] == "PASS"
