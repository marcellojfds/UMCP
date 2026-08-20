"""Legacy protocol helpers and non-MCP health hosting.

The public Alpha transport is implemented by ``omp.server.official`` using the
installed official MCP SDK. ``MCPJSONRPCServer`` remains a dependency-light
contract harness only; it is not the supported public server transport.
"""

import asyncio
import json
import sys
from collections.abc import AsyncIterator, Iterable, Mapping
from typing import Any, cast

from .adapter import MCPAdapter
from .schemas import (
    MCP_PROTOCOL_VERSION,
    ForgetRequest,
    SearchRequest,
    UpdateRequest,
    WriteRequest,
)

TOOL_DESCRIPTIONS = {
    "memory.write": (
        "Persist one explicitly selected memory. Call only when the caller has a durable "
        "fact, preference, decision, insight, or similar item; do not send a conversation dump."
    ),
    "memory.search": (
        "Search the user's memory conservatively. An empty result is a successful abstention; "
        "do not lower the threshold merely to force a result."
    ),
    "memory.update": (
        "Update one memory using optimistic concurrency. expected_version is required and "
        "stale versions return version_conflict."
    ),
    "memory.forget": "Forget one memory idempotently. The result never echoes deleted content.",
}


class MCPJSONRPCServer:
    def __init__(self, adapter: MCPAdapter) -> None:
        self.adapter = adapter

    async def handle(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        if message.get("jsonrpc") != "2.0" or "method" not in message:
            return self._rpc_error(message.get("id"), -32600, "invalid request")
        method = message["method"]
        request_id = message.get("id")
        if request_id is None:
            if method in {"notifications/initialized", "notifications/cancelled"}:
                return None
            return self._rpc_error(None, -32600, "request id required")
        params = message.get("params") or {}
        if not isinstance(params, Mapping):
            return self._rpc_error(request_id, -32602, "invalid params")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "open-memory-protocol", "version": "0.1.0a1"},
                    "instructions": (
                        "Use the four memory tools conservatively; zero search results are valid."
                    ),
                },
            }
        if method in {"tools/list", "omp/capabilities"}:
            result = (
                self._tools_list()
                if method == "tools/list"
                else self.adapter.capabilities(str(request_id))
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            envelope = await self.adapter.call_tool(
                str(name), arguments, request_id=str(request_id)
            )
            text = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "structuredContent": envelope,
                    "isError": not envelope.get("ok", False),
                },
            }
        return self._rpc_error(request_id, -32601, "method not found")

    def _tools_list(self) -> dict[str, Any]:
        schemas = {
            "memory.write": WriteRequest,
            "memory.search": SearchRequest,
            "memory.update": UpdateRequest,
            "memory.forget": ForgetRequest,
        }
        return {
            "tools": [
                {
                    "name": name,
                    "description": TOOL_DESCRIPTIONS[name],
                    "inputSchema": cast(Any, schemas[name]).model_json_schema(),
                }
                for name in self.adapter.TOOLS
            ]
        }

    @staticmethod
    def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


async def serve_messages(
    messages: AsyncIterator[Mapping[str, Any]], server: MCPJSONRPCServer
) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    async for message in messages:
        response = await server.handle(message)
        if response is not None:
            responses.append(response)
    return responses


def run_stdio(
    adapter: MCPAdapter, *, input_stream: Iterable[str] | None = None, output_stream: Any = None
) -> None:
    """Run newline-delimited JSON-RPC over stdio.

    No request payload is logged. Operational logs must go to stderr.
    """

    source = input_stream if input_stream is not None else sys.stdin
    sink = output_stream if output_stream is not None else sys.stdout
    server = MCPJSONRPCServer(adapter)
    for line in source:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = asyncio.run(server.handle(message))
            if response is not None:
                sink.write(
                    json.dumps(response, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    + "\n"
                )
                sink.flush()
        except json.JSONDecodeError:
            sink.write(json.dumps(server._rpc_error(None, -32700, "parse error")) + "\n")
            sink.flush()


def create_health_app(adapter: MCPAdapter, readiness: Any | None = None) -> Any:
    """Create FastAPI liveness/readiness only; this is not an MCP transport."""

    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
    except ImportError as exc:  # pragma: no cover - only used in minimal installs
        raise RuntimeError("FastAPI is required for health/readiness hosting") from exc

    app = FastAPI(title="Open Memory Protocol", version="0.1.0a1")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        check = readiness or getattr(adapter.service, "readiness", None)
        try:
            outcome = check() if check else True
            if hasattr(outcome, "__await__"):
                outcome = await outcome
        except BaseException:
            outcome = False
        if outcome is False:
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return JSONResponse({"status": "ready"}, status_code=200)

    return app


create_http_app = create_health_app
