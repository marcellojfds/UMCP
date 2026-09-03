# Current deployed state

**Last reconciled:** 2026-09-02
**Environment:** private GCP staging  
**Canonical source:** `05b4a8eac282721eb4a7de5ecd511ce8e618a37c`

## Deployment

| Field | Current value |
| --- | --- |
| GCP project | `umcp-mcp-staging-20260825` |
| Region | `us-central1` |
| Cloud Run service | `umcp-cloud-staging` |
| Active revision | `umcp-cloud-staging-claude-final5` |
| MCP endpoint | `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp` |
| Portal | `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/` |
| Image digest | `sha256:c4467b47e88329081303978d3ff6f22f2edd8f096d711c6c2756d604ec0a3c45` |

Staging is allowlisted for the maintainer identity. It is not production,
public beta, or a general availability claim.

## Verified user journey

1. A compatible MCP client discovers UMCP's protected-resource and OAuth
   metadata.
2. UMCP redirects the authorization request to Google.
3. The verified Google subject is deterministically mapped to one UMCP user,
   tenant, membership, and owner scope.
4. The client receives scoped UMCP tokens; raw Google identity is not used as
   a caller-supplied `owner_id`.
5. ChatGPT can store a durable memory with `memory.capture`/`memory.write`.
6. The same user can sign into the portal and inspect stored memories.
7. Gemini Spark can connect as `@Umcp Cloud` and retrieve the same owner's
   memory.

The 2026-08-30 cross-surface check returned:

```text
A sua cor favorita é roxo.
```

from the exact stored memory:

```text
A cor favorita de Marcello é roxo.
```

## What is implemented

- Streamable HTTP MCP at exact path `/mcp`.
- Google-backed authorization-code flow with PKCE.
- Protected-resource and authorization-server metadata.
- Access/refresh token issuance, rotation, expiry, and revocation ledgers.
- Server-derived hosted owner/tenant context.
- `memory.write`, `memory.search`, `memory.capture`, `memory.update`, and
  `memory.forget`.
- Owner portal session, list, detail, and logout endpoints.
- Authenticated personal-vault shell with persistent account navigation, search,
  memory cards, pinned notes, and memory detail inspector.
- In-app portal transitions without full-page reloads, working memory filters
  and list/card views, and an Inbox review queue derived from owner memories.
- Read-only capability gating for account controls that are not supported by
  the current hosted API.
- No-store portal assets with explicit entrypoint versioning, plus transparent
  rotation of the short-lived portal access session through an HttpOnly refresh
  cookie.
- PostgreSQL/pgvector persistence and hosted tenant context.
- Deployment provenance headers and immutable image/source metadata.
- Actionable portal onboarding for ChatGPT, Claude Code, and Gemini, including
  the exact hosted MCP endpoint, OAuth steps, verification commands, and
  staging/account prerequisites.

## Acceptance by surface

| Surface | Current evidence |
| --- | --- |
| ChatGPT connected app | OAuth and owner-scoped capture exercised in the maintainer account |
| Gemini consumer | Custom app connected in Gemini Spark; tools synchronized; exact owner memory retrieved |
| UMCP portal | Google login and owner memory list/detail exercised |
| Claude Code | Remote HTTP server registered; UMCP OAuth completed; client reports `Connected`. Model-driven tool execution remains blocked because the tested Anthropic account has neither Claude Pro/Max nor an API key with credits |
| Local agents | Python SDK, CLI, stdio, and deterministic connector tests exist |

## Open defects

1. **Retrieval calibration:** `memory.search` defaults to
   `min_relevance=0.78`; the verified Gemini recall returned zero until the
   caller used `0.0`.
2. **Provenance labeling:** `memory.capture` currently hardcodes
   `source_model="chatgpt"` for every hosted client.
3. **Natural invocation:** Gemini Spark asks for tool approval and may broaden
   a vague prompt to unrelated Google apps unless explicitly constrained.
4. **Documentation/publication:** no production domain, public beta policy,
   SLA, or release artifact has been approved.
5. **Claude model acceptance:** the MCP/OAuth handshake is verified, but an
   end-to-end model-driven write/search/update/forget run still requires a
   Claude Pro/Max account or an Anthropic API key with available credits.

See [Claude Code OAuth acceptance](handoffs/roadmap/CLAUDE-CODE-OAUTH-ACCEPTANCE-20260902.md),
[Known issues](known-issues.md), and [Roadmap](roadmap.md) for remediation.
