# MCP v0 contracts

The runtime source of truth is `src/omp/adapters/mcp/schemas.py`; the JSON
files in this directory are the checked-in public machine-readable snapshot.
The contract version is `omp.mcp.v0`. Unknown fields are rejected.

The supported tool names are exactly `memory.write`, `memory.search`,
`memory.update` and `memory.forget`. `memory.related` is not part of v0.

Alpha transport is MCP stdio via the official `mcp` package; the negotiated
SDK protocol is `2025-11-25`. HTTP is health/readiness only, not MCP
Streamable HTTP. Public responses use the OMP protocol version and request ID;
`min_relevance` defaults to `0.78`.
