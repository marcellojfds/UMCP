# UMCP protocol reference

UMCP has two protocol surfaces that share the application core but use
different identity contracts.

## Hosted Cloud MCP

- Transport: MCP Streamable HTTP at exact path `/mcp`.
- Authentication: UMCP OAuth discovery, authorization code + PKCE, scoped
  UMCP access/refresh tokens.
- Identity: derived from verified token claims; hosted tools reject client
  `owner_id` and `tenant_id`.
- Tools: `memory.write`, `memory.search`, `memory.capture`, `memory.update`,
  `memory.forget`.
- Contract reference: [`contracts/mcp/v1/`](contracts/mcp/v1/).

The public endpoint is stateless. `/mcp/` is not an alias for `/mcp`, avoiding
redirect and proxy-scheme ambiguity. Health/readiness use `/healthz` and
`/readyz` and never expose configuration or identity.

## Local Community MCP

- Transport: official MCP Python SDK over stdio.
- Identity: trusted caller-provided `owner_id`.
- Tools: `memory.write`, `memory.search`, `memory.update`, `memory.forget`.
- Compatibility envelope: `omp.mcp.v0`.
- Contract reference: [`contracts/mcp/v0/`](contracts/mcp/v0/).

The local composition is not an authentication boundary and must not be
exposed directly to untrusted users.

## Shared behavior

- Unknown fields are rejected.
- Content limit: 16,384 characters.
- Query limit: 4,096 characters.
- Search result limit: 50.
- `update` requires `expected_version`.
- Write/update/forget are idempotency-aware.
- Search with no result is a successful response with count zero.
- Public errors use stable codes and omit SQL, stack traces, tokens, raw
  identity, memory content, and queries.

`memory.search` currently defaults to `min_relevance=0.78`. This is a known
calibration defect in the private staging user journey; see
[`known-issues.md`](known-issues.md).

## Hosted OAuth metadata

- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-protected-resource/mcp`
- `/.well-known/oauth-authorization-server`
- `/authorize`
- `/token`
- `/revoke`

Supported scopes are `memory:read`, `memory:write`, and `memory:delete`.

## Administrative export/import

`omp.export.v0` remains a local administrative format. Exports are owner-
scoped and omit embeddings by default, but the file, history, provenance, and
relations remain sensitive. Export/import is not an additional hosted MCP
tool in the current MVP.
