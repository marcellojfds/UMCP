"""Application composition and MCP stdio entrypoints."""

from __future__ import annotations

from typing import Any

from omp.adapters.mcp.adapter import MCPAdapter
from omp.adapters.mcp.application_gateway import MemoryApplicationGateway
from omp.adapters.mcp.transport import create_health_app as _create_health_app
from omp.server.composition import ServerRuntime, create_demo_runtime, create_runtime
from omp.server.official import create_official_server, run_stdio


def create_mcp_adapter(
    service: Any, *, local_mode: bool = True, transport: str = "stdio"
) -> MCPAdapter:
    """Compose the MCP boundary around an explicitly injected service."""
    selected = service
    if selected.__class__.__name__ == "MemoryApplicationService":
        selected = MemoryApplicationGateway(selected)
    return MCPAdapter(selected, local_mode=local_mode, transport=transport)


def create_health_app(runtime: ServerRuntime) -> Any:
    """Compose the non-MCP liveness/readiness ASGI app for a runtime."""

    return _create_health_app(runtime.adapter, runtime.readiness)


__all__ = [
    "ServerRuntime",
    "create_demo_runtime",
    "create_health_app",
    "create_mcp_adapter",
    "create_official_server",
    "create_runtime",
    "run_stdio",
]
