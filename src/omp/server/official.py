"""Official MCP SDK server composition for the supported stdio transport."""

from __future__ import annotations

import json
from typing import Annotated

import anyio
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from omp.adapters.mcp.schemas import (
    DEFAULT_TIMEOUT_MS,
    MAX_CONTENT_LENGTH,
    MAX_QUERY_LENGTH,
    MAX_TIMEOUT_MS,
    MemoryPatch,
    MemoryState,
    MemoryType,
    Provenance,
)

from .composition import ServerRuntime


def create_official_server(runtime: ServerRuntime) -> FastMCP:
    server = FastMCP(
        name="open-memory-protocol",
        instructions=(
            "Use the four memory tools conservatively; an empty search is a valid abstention."
        ),
    )

    @server.tool(name="memory.write", structured_output=False)
    async def memory_write(
        content: Annotated[str, Field(min_length=1, max_length=MAX_CONTENT_LENGTH)],
        type: MemoryType,
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        provenance: Provenance,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        space: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        importance: Annotated[float, Field(ge=0, le=1)] = 0.5,
        confidence: Annotated[float, Field(ge=0, le=1)] = 0.5,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.write", locals())

    @server.tool(name="memory.search", structured_output=False)
    async def memory_search(
        query: Annotated[str, Field(min_length=1, max_length=MAX_QUERY_LENGTH)],
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        space: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        type: MemoryType | None = None,
        state: MemoryState | None = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
        min_relevance: Annotated[float, Field(ge=0, le=1)] = 0.78,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.search", locals())

    @server.tool(name="memory.update", structured_output=False)
    async def memory_update(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        expected_version: Annotated[int, Field(ge=1)],
        patch: MemoryPatch,
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        provenance: Provenance | None = None,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.update", locals())

    @server.tool(name="memory.forget", structured_output=False)
    async def memory_forget(
        id: Annotated[str, Field(min_length=1, max_length=128)],
        owner_id: Annotated[str, Field(min_length=1, max_length=128)],
        idempotency_key: Annotated[str, Field(min_length=1, max_length=128)],
        reason: Annotated[str | None, Field(max_length=256)] = None,
        timeout_ms: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_MS)] = DEFAULT_TIMEOUT_MS,
    ) -> str:
        return await _call(runtime, "memory.forget", locals())

    for tool in server._tool_manager._tools.values():  # official SDK tool registry
        tool.parameters["additionalProperties"] = False

    return server


async def _call(runtime: ServerRuntime, name: str, values: dict[str, object]) -> str:
    arguments = {key: value for key, value in values.items() if key not in {"runtime", "name"}}
    envelope = await runtime.adapter.call_tool(name, arguments)
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


async def serve_stdio(runtime: ServerRuntime) -> None:
    server = create_official_server(runtime)
    try:
        await runtime.startup()
        await server.run_stdio_async()
    finally:
        await runtime.close()


def run_stdio(runtime: ServerRuntime) -> None:
    anyio.run(serve_stdio, runtime)
