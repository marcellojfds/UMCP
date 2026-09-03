# Support and verification matrix

**Last reconciled:** 2026-09-02

“Verified” below means one dated journey succeeded in the maintainer's private
staging account. It does not imply general availability, marketplace approval,
scale, or a production SLA.

| Surface | Status | Current evidence and limitation |
| --- | --- | --- |
| ChatGPT connected app | **Verified in private staging** | OAuth and owner-scoped memory capture exercised against the hosted `/mcp` endpoint |
| Gemini Spark custom app | **Verified in private staging** | OAuth, tool synchronization, and exact cross-surface recall succeeded; default retrieval threshold required an explicit `min_relevance=0.0` workaround |
| UMCP owner portal | **Verified in private staging** | Same Google identity can list and inspect owner-scoped memories |
| Gemini normal chat | **Not supported by this custom-app path** | Use Spark and select `@Umcp Cloud` |
| Claude Code | **OAuth/MCP handshake verified in private staging** | Claude Code 2.1.236 completed UMCP OAuth and reported the remote server `Connected` on 2026-09-02; model-driven lifecycle remains unverified because the available Anthropic account has neither Pro/Max access nor an API key |
| Claude Desktop / API | **Not verified** | Separate surfaces; no current real-account lifecycle report |
| Python agents | **Implemented/tested locally** | Python SDK, OAuth transport, controlled agent, and local/hosted audit runners exist |
| TypeScript agents | **Experimental** | Transport-agnostic scaffold; no complete hosted acceptance |
| Community stdio MCP | **Implemented/tested locally** | Caller-provided `owner_id`; trusted local boundary only |

## Platform and backend boundary

| Area | Current status |
| --- | --- |
| Python | 3.11 is the tested project runtime |
| Database | PostgreSQL 16 + pgvector; migrations through the hosted OAuth schema |
| Hosted transport | MCP Streamable HTTP at exact `/mcp` |
| Local transport | Official MCP Python SDK over stdio |
| Hosted identity | Google OAuth through UMCP; owner/tenant derived server-side |
| Hosted tools | `memory.write`, `memory.search`, `memory.capture`, `memory.update`, `memory.forget` |
| Local tools | `memory.write`, `memory.search`, `memory.update`, `memory.forget` |
| Distribution | Source repository and private staging only; no production release or PyPI publication |

## Trust boundary

Hosted requests reject caller-supplied `owner_id` and `tenant_id`; the service
derives scope from a verified UMCP token. Local stdio remains a trusted-client
composition and must not be placed directly on an untrusted network.

See [Current state](CURRENT_STATE.md), [Known issues](known-issues.md),
[Privacy](privacy.md), and the [hosted threat model](threat-model-hosted-v1.md).
