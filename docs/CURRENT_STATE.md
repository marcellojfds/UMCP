# Current deployed state

**Last reconciled:** 2026-08-31
**Environment:** private GCP staging  
**Canonical source:** `820760f`

## Deployment

| Field | Current value |
| --- | --- |
| GCP project | `umcp-mcp-staging-20260825` |
| Region | `us-central1` |
| Cloud Run service | `umcp-cloud-staging` |
| Active revision | `umcp-cloud-staging-portal-session` |
| MCP endpoint | `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp` |
| Portal | `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/` |
| Image digest | `sha256:88c95d5232f6a676d19a51a2db6de96eb7da168a626716c0850014835d528ab7` |

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

## Acceptance by surface

| Surface | Current evidence |
| --- | --- |
| ChatGPT connected app | OAuth and owner-scoped capture exercised in the maintainer account |
| Gemini consumer | Custom app connected in Gemini Spark; tools synchronized; exact owner memory retrieved |
| UMCP portal | Google login and owner memory list/detail exercised |
| Claude | No equivalent current real-account acceptance |
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

See [Known issues](known-issues.md) and [Roadmap](roadmap.md) for remediation.
