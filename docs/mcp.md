# MCP integration

Open Memory Protocol Alpha supports only the official MCP Python SDK over
stdio. The negotiated MCP SDK protocol observed in the Alpha handoff is
`2025-11-25`; the independent OMP contract is `omp.mcp.v0`.

## Start the server

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' OMP_BACKEND=postgres \
  python -m omp.server
```

The server requires PostgreSQL + pgvector and the migration head. It does not
silently switch to the demo/file backend. HTTP, when enabled by the
application, is limited to `/healthz` and `/readyz`; it is not MCP transport.

## Tools

The server exposes exactly four tools:

- `memory.write`
- `memory.search`
- `memory.update`
- `memory.forget`

Requests reject unknown fields. Public limits include 16,384 characters per
memory, 4,096 characters per query, a maximum result limit of 50, and a
default timeout of 2,500 ms with a 5,000 ms maximum. `update` requires
`expected_version`; `forget` is transactional and returns only
`forgotten`/`already_absent`.

## Identity and privacy boundary

In local stdio composition, `owner_id` comes from the client payload and is
trusted. It provides logical owner scoping in the tested local composition; it
is not authentication, authorization, or tenant isolation. Do not expose this
composition to untrusted users. A hosted identity boundary is not implemented.

The server's logging contract omits content, query, provenance, vectors, raw
owner IDs, and secrets by default. This reduces accidental disclosure but does
not protect data from an operator, database dump, process compromise, export,
or backup.

See the [versioned MCP schemas](contracts/mcp/v0/README.md) and the deeper
[protocol reference](protocol.md).
