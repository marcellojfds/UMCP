# Changelog

All notable changes are recorded here. UMCP has not published a production
release or PyPI package.

## Unreleased — private staging MVP

### Added

- Hosted Streamable HTTP MCP at the exact `/mcp` path.
- OAuth authorization-code flow with PKCE and Google identity.
- Server-derived owner and tenant scope for hosted MCP calls.
- `memory.capture` for concise durable facts from assistant conversations.
- Same-origin owner portal with Google login and memory inspection.
- Static OAuth client support for ChatGPT and Gemini custom connected apps.
- Cloud PostgreSQL/pgvector persistence, RLS-oriented tenant boundaries,
  envelope-encryption integration, and hosted recovery/audit paths.

### Verified on 2026-08-30

- ChatGPT connected to staging, authenticated, and stored owner-scoped memory.
- Gemini Spark connected to the same OAuth identity and synchronized all five
  memory actions.
- Gemini retrieved an exact preference written to the same UMCP owner vault.
- The portal displayed memories for the signed-in owner.
- Deployed source SHA:
  `1233b221fd89edb1691bd6bd09c2d21eee4822bf`.

### Known limitations

- Default semantic relevance can suppress a valid memory; the verified Gemini
  lookup required `min_relevance=0.0`.
- `memory.capture` currently records `source_model="chatgpt"` even when invoked
  by another client.
- Gemini custom apps work through Gemini Spark and require an explicit tool
  approval in the tested flow.
- Claude has not completed the same real-account acceptance journey.
- Staging is a private test environment, not a public beta or production SLA.

## 0.1.0a1 — historical local engineering preview

The original alpha established the domain model, PostgreSQL/pgvector
repository, local stdio MCP, Python SDK, CLI, export/import, evaluations, and
privacy/security baselines. Historical reports remain under
`docs/handoffs/alpha/` and `evals/reports/`.
