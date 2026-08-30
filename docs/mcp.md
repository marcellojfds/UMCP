# MCP integration

UMCP implements a local stdio composition and an authenticated hosted
Streamable HTTP composition. They intentionally have different identity
boundaries.

## Hosted MCP

Endpoint:

```text
https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp
```

The endpoint is stateless Streamable HTTP and uses OAuth discovery. Hosted
tool schemas do not accept `owner_id` or `tenant_id`; UMCP derives the internal
owner from verified token claims and enters tenant scope before accessing the
application service.

Hosted tools:

- `memory.write`
- `memory.search`
- `memory.capture`
- `memory.update`
- `memory.forget`

`memory.capture` is the assistant-oriented convenience tool for one concise,
durable fact. It should be used only for an explicit remember request or
clearly useful long-term context, never for secrets, credentials, or transient
details.

## OAuth endpoints

- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-protected-resource/mcp`
- `/.well-known/oauth-authorization-server`
- `/authorize` and `/oauth/authorize`
- `/oauth/callback`
- `/token`
- `/revoke`

The hosted authorization flow uses authorization code + PKCE. UMCP exchanges
with Google for identity, then issues its own scoped access and refresh tokens.
Stored state, authorization codes, and tokens are digested; bearer values must
never appear in documentation, logs, or browser storage.

## Scopes

- `memory:read`
- `memory:write`
- `memory:delete`

Tools enforce their corresponding scope even when a client presents a valid
token.

## Search behavior

`memory.search` accepts `query`, optional `space`, `type`, `state`, `limit`,
and `min_relevance`. The current default relevance threshold is `0.78` and is
a known staging defect for direct recall. Do not make it the permanent client
workaround; calibrate the server policy instead.

## Local stdio

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' OMP_BACKEND=postgres \
  python -m omp.server
```

The local tool schemas require caller-provided `owner_id`. This is logical
scoping for a trusted local client, not hosted authentication. Never expose the
local composition directly to untrusted callers.

See the [protocol reference](protocol.md), [versioned schemas](contracts/mcp/),
[current state](CURRENT_STATE.md), and [known issues](known-issues.md).
