from __future__ import annotations

import asyncio
import json
import logging
from io import StringIO
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest

from omp.adapters.mcp.adapter import FixedRateLimiter, MCPAdapter, TenantWindowRateLimiter
from omp.adapters.mcp.errors import PublicErrorCode
from omp.adapters.mcp.fakes import InMemoryMemoryService
from omp.adapters.mcp.schemas import PROTOCOL_VERSION, WriteRequest
from omp.adapters.mcp.transport import MCPJSONRPCServer
from omp.cloud.tenant import tenant_scope
from omp.sdk.client import (
    InProcessTransport,
    MemoryClient,
    OfficialStdioTransport,
    ProtocolError,
)


def test_shared_application_service_gateway_round_trip() -> None:
    from omp.adapters.embeddings.hash_provider import HashEmbeddingProvider
    from omp.adapters.mcp.application_gateway import MemoryApplicationGateway
    from omp.application.fakes import InMemoryUnitOfWorkFactory
    from omp.application.services import MemoryApplicationService

    service = MemoryApplicationService(
        uow_factory=cast(Any, InMemoryUnitOfWorkFactory()),
        embedding_provider=HashEmbeddingProvider(),
    )
    client = MemoryClient(InProcessTransport(MCPAdapter(MemoryApplicationGateway(service))))
    result = client.write(**write_args())
    memory_id = result["memory"]["id"]
    assert result["status"] == "created"
    updated = client.update(
        id=memory_id,
        owner_id="owner-a",
        expected_version=1,
        patch={"importance": 0.9},
        provenance=provenance(),
        idempotency_key="core-update",
    )
    assert updated["memory"]["version"] == 2
    assert (
        client.forget(id=memory_id, owner_id="owner-a", idempotency_key="core-forget")["status"]
        == "forgotten"
    )


FIXTURES = Path(__file__).parent / "fixtures"


def provenance() -> dict[str, str]:
    return {
        "source_type": "conversation",
        "captured_at": "2026-01-01T12:00:00Z",
        "source_id": "synthetic-mba-001",
    }


def write_args(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "content": "Geographic density should precede expansion for local-network marketplaces.",
        "type": "insight",
        "owner_id": "owner-a",
        "importance": 0.82,
        "confidence": 0.76,
        "provenance": provenance(),
        "idempotency_key": "write-mba-001",
    }
    value.update(overrides)
    return value


def test_golden_request_and_response_schema() -> None:
    request = json.loads((FIXTURES / "write.request.json").read_text())
    assert WriteRequest.model_validate(request).type == "insight"
    response = json.loads((FIXTURES / "write.response.json").read_text())
    assert response["protocol_version"] == PROTOCOL_VERSION
    assert response["data"]["status"] == "created"


def test_four_tools_are_discoverable_with_strict_schemas() -> None:
    server = MCPJSONRPCServer(MCPAdapter(InMemoryMemoryService()))
    listed = asyncio.run(
        server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    )
    assert listed is not None
    tools = listed["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "memory.write",
        "memory.search",
        "memory.update",
        "memory.forget",
    ]
    assert all(tool["inputSchema"]["additionalProperties"] is False for tool in tools)


def test_validation_happens_before_application_service() -> None:
    class CountingService(InMemoryMemoryService):
        def write(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.called = True
            return super().write(payload)

    service = CountingService()
    result = asyncio.run(
        MCPAdapter(service).call_tool("memory.write", {**write_args(), "unknown": True})
    )
    assert result["ok"] is False
    assert result["error"]["code"] == PublicErrorCode.VALIDATION
    assert not hasattr(service, "called")


def test_limits_timeout_and_cancellation() -> None:
    service = InMemoryMemoryService()
    adapter = MCPAdapter(service)
    too_long = asyncio.run(
        adapter.call_tool("memory.search", {"query": "x" * 4097, "owner_id": "a"})
    )
    assert too_long["error"]["code"] == "validation_error"

    class SlowService(InMemoryMemoryService):
        async def search(self, payload: dict[str, Any]) -> list[Any]:
            await asyncio.sleep(0.05)
            return []

    slow = MCPAdapter(SlowService())
    timed = asyncio.run(
        slow.call_tool("memory.search", {"query": "x", "owner_id": "a", "timeout_ms": 1})
    )
    assert timed["error"]["code"] == "dependency_unavailable"

    async def cancelled() -> None:
        task = asyncio.create_task(
            slow.call_tool("memory.search", {"query": "x", "owner_id": "a", "timeout_ms": 5000})
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancelled())


def test_zero_results_conflict_forget_and_cross_owner_isolation() -> None:
    client = MemoryClient(InProcessTransport(MCPAdapter(InMemoryMemoryService())))
    written = client.write(**write_args())
    memory_id = written["memory"]["id"]
    assert client.search(query="irrelevant recipe", owner_id="owner-a")["memories"] == []
    assert client.search(query="geographic density", owner_id="owner-b")["memories"] == []
    with pytest.raises(ProtocolError) as conflict:
        client.update(
            id=memory_id,
            owner_id="owner-a",
            expected_version=9,
            patch={"content": "x"},
            provenance=provenance(),
            idempotency_key="bad",
        )
    assert conflict.value.code == "version_conflict"
    with pytest.raises(ProtocolError) as hidden:
        client.update(
            id=memory_id,
            owner_id="owner-b",
            expected_version=1,
            patch={"content": "x"},
            provenance=provenance(),
            idempotency_key="cross",
        )
    assert hidden.value.code == "not_found"
    assert (
        client.forget(id=memory_id, owner_id="owner-a", idempotency_key="forget")["status"]
        == "forgotten"
    )
    assert (
        client.forget(id=memory_id, owner_id="owner-a", idempotency_key="forget-2")["status"]
        == "already_absent"
    )
    assert client.search(query="geographic density", owner_id="owner-a")["memories"] == []


def test_error_messages_and_logs_do_not_leak_canary() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test-omp-mcp")
    logger.handlers[:] = [handler]
    logger.setLevel(logging.INFO)
    canary = "CANARY-DO-NOT-LOG-7f9a"
    adapter = MCPAdapter(
        InMemoryMemoryService(),
        logger=__import__(
            "omp.adapters.mcp.observability", fromlist=["StructuredLogger"]
        ).StructuredLogger(logger),
    )
    result = asyncio.run(adapter.call_tool("memory.write", write_args(content=canary)))
    assert result["ok"] is True
    assert canary not in stream.getvalue()
    assert "owner-a" not in stream.getvalue()
    bad = asyncio.run(
        adapter.call_tool(
            "memory.search", {"query": canary, "owner_id": "owner-a", "unknown": "secret"}
        )
    )
    assert bad["error"]["code"] == "validation_error"
    assert canary not in json.dumps(bad)
    assert canary not in stream.getvalue()


def test_rate_limit_and_hosted_owner_boundary() -> None:
    limited = MCPAdapter(InMemoryMemoryService(), rate_limiter=FixedRateLimiter(0))
    result = asyncio.run(limited.call_tool("memory.search", {"query": "x", "owner_id": "a"}))
    assert result["error"]["code"] == "rate_limited"
    hosted = MCPAdapter(InMemoryMemoryService(), local_mode=False)
    result = asyncio.run(hosted.call_tool("memory.search", {"query": "x", "owner_id": "a"}))
    assert result["error"]["code"] == "forbidden"


def test_cloud_rate_limit_isolated_per_verified_tenant() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    adapter = MCPAdapter(
        InMemoryMemoryService(), rate_limiter=TenantWindowRateLimiter(maximum=1)
    )
    with tenant_scope(tenant_a):
        first = asyncio.run(adapter.call_tool("memory.search", {"query": "x", "owner_id": "a"}))
        limited = asyncio.run(
            adapter.call_tool("memory.search", {"query": "x", "owner_id": "a"})
        )
    assert first["ok"] is True
    assert limited["error"]["code"] == "rate_limited"
    with tenant_scope(tenant_b):
        other_tenant = asyncio.run(
            adapter.call_tool("memory.search", {"query": "x", "owner_id": "b"})
        )
    assert other_tenant["ok"] is True


def test_mcp_server_and_sdk_compatibility() -> None:
    server = MCPJSONRPCServer(MCPAdapter(InMemoryMemoryService()))
    initialized = asyncio.run(
        server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    )
    assert initialized is not None
    assert initialized["result"]["protocolVersion"] == "2025-11-25"
    sdk = MemoryClient(InProcessTransport(server.adapter))
    assert sdk.write(**write_args())["status"] == "created"


def test_official_mcp_stdio_client_compatibility(tmp_path: Path) -> None:
    from omp.config import OMPSettings
    from omp.server.composition import create_demo_runtime
    from omp.server.official import create_official_server

    runtime = create_demo_runtime(OMPSettings(demo_data_file=str(tmp_path / "schema.json")))
    server = create_official_server(runtime)
    assert all(
        tool.parameters["additionalProperties"] is False
        for tool in server._tool_manager._tools.values()
    )
    client = MemoryClient(
        OfficialStdioTransport(
            demo_backend=True,
            data_file=str(tmp_path / "official.json"),
        )
    )
    capabilities = client.capabilities()
    assert capabilities["mcp_protocol_version"] == "2025-11-25"
    assert capabilities["transport"] == "stdio"
    assert capabilities["tools"] == [
        "memory.write",
        "memory.search",
        "memory.update",
        "memory.forget",
    ]
    assert client.write(**write_args())["status"] == "created"


def test_http_health_readiness_has_no_mcp_route() -> None:
    from fastapi.testclient import TestClient

    from omp.adapters.mcp.transport import create_http_app

    app = create_http_app(MCPAdapter(InMemoryMemoryService()))
    client = TestClient(app)
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}
    response = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    assert response.status_code == 404
