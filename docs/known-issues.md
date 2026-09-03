# Known issues

**Updated:** 2026-09-02
**Applies to:** private staging MVP at source
`05b4a8eac282721eb4a7de5ecd511ce8e618a37c`

## P0 — retrieval threshold hides relevant memories

`memory.search` defaults to `min_relevance=0.78`. In the verified Gemini Spark
journey, searches for `cor` and `cor favorita` returned no result at the
default. The same query returned the correct stored preference with
`min_relevance=0.0`.

Impact: a connected client can appear unable to share memory even though OAuth,
owner binding, storage, and MCP calls are working.

Temporary diagnostic workaround:

```text
Use only Umcp Cloud memory.search with query "cor favorita", limit 10,
and min_relevance 0.0.
```

This workaround is not the intended user experience. The fix requires profile-
specific calibration plus positive and abstention regressions.

## P1 — capture provenance is ChatGPT-specific

Hosted `memory.capture` currently writes `source_model="chatgpt"` for every
caller. A capture initiated by Gemini would therefore be mislabeled.

Until fixed, provenance identifies the UMCP conversation capture path but must
not be used to attribute the client reliably.

## P1 — Gemini custom apps require Spark

The tested Gemini consumer integration is available under Gemini Spark, not
the normal Gemini chat surface. The user must type `@`, select **Umcp Cloud**,
and approve the requested tool action. Vague prompts may cause Spark to search
other connected Google apps.

For deterministic testing, explicitly say to use only `Umcp Cloud`.

## P1 — staging access is allowlisted

The Google OAuth server currently allows only the configured maintainer email
digest. Other users will receive an authorization denial. This is intentional
for private staging and must be replaced by an approved beta enrollment policy
before invitations.

## P2 — incomplete client coverage

- ChatGPT and Gemini have maintainer-account evidence only.
- Claude Code 2.1.236 completed OAuth and reports the hosted UMCP server as
  `Connected`, but the available Anthropic account has neither Pro/Max model
  access nor an API key. A model-driven write/search/update/forget report is
  therefore still missing.
- Gemini normal chat, Gemini CLI, Gemini API/ADK, Claude Desktop, Claude API, and
  published marketplace applications must be evaluated separately.

## P2 — repository quality gates are not green

The validation run on 2026-09-02 produced these results:

- Markdown link/claim check: pass across 229 files;
- portal web tests: 26 passed;
- Python unit and contract suite: 147 passed and 7 failed;
- `gate-fast`: blocked by 126 existing Ruff findings; and
- `mypy src`: blocked by 32 existing type errors.

Three Python failures require the optional M1 HTTP endpoint configured by
`M1_HTTP_URL`. Two package-entrypoint checks currently fail because
`python3 -m omp.server` is not an implemented module command. The remaining two
expose unresolved M1 Streamable HTTP contract regressions: the exact `/mcp`
test receives 404 and the rerunnable lifecycle test terminates its session.
These are pre-existing implementation debt, not Claude onboarding failures,
and must not be represented as a green release gate.

## Non-claims

UMCP staging is not production, E2EE, zero knowledge, universally compatible,
or a public beta. Operators with authorized access to the service, database,
keys, exports, or backups may be able to access plaintext. Embeddings are not
anonymous.
