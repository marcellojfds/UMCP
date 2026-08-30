# Current deployed state

**Last reconciled:** 2026-08-30  
**Environment:** private GCP staging  
**Canonical source:** `1233b221fd89edb1691bd6bd09c2d21eee4822bf`

## Deployment

| Field | Current value |
| --- | --- |
| GCP project | `umcp-mcp-staging-20260825` |
| Region | `us-central1` |
| Cloud Run service | `umcp-cloud-staging` |
| Active revision | `umcp-cloud-staging-chatgpt-mvp2` |
| MCP endpoint | `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp` |
| Portal | `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/` |
| Image digest | `sha256:689666f65458dee80f9fbade2b78c32fdab7235ac09b42b91adc0ca55ef1028d` |

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
