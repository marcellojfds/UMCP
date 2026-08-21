# ADR 0010 — MCP Streamable HTTP and separate administrative API

## Status

Accepted for productization design (2026-08-21).

## Decision

Preserve stdio as the Community transport. Cloud mounts MCP Streamable HTTP
only at `/mcp`; health and readiness remain `/healthz` and `/readyz` and never
return tenant, principal, database, secret, token, query, or memory data. The
gateway implements MCP initialize, discovery, `tools/list`, `tools/call`, and
protocol streaming using the official SDK/runtime selected during implementation.

Dashboard, connections, PATs, exports and account deletion use a separately
versioned administrative API. Both transports call the same application
services. SSE is not a default requirement; it is added only behind a tested
compatibility adapter when a client requires it.

## Consequences

Conformance tests compare stdio and HTTP outputs after normalizing transport
metadata. `/mcp` may not become a generic REST endpoint. Every public tool is
annotated read-only, write, or destructive and its required scope.
