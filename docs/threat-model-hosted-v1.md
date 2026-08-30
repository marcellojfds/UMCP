# Threat model — UMCP hosted v1

**Status:** implemented private-staging baseline; production review pending.
**Updated:** 2026-08-30.

## Boundaries and assets

```text
untrusted MCP client
  -> HTTPS Cloud Run endpoint
  -> UMCP OAuth token verification
  -> server-derived Principal / tenant scope
  -> application service
  -> PostgreSQL + pgvector / tenant controls
  -> KMS-backed encryption path

Google OAuth -> UMCP identity mapping -> UMCP token ledgers
Portal browser -> Secure HttpOnly UMCP session -> same-origin portal API
```

Assets include memory content, provenance, embeddings, tenant membership,
authorization codes, access/refresh tokens, portal sessions, encryption keys,
exports, deletion state, audit records, and backups.

## Primary threats and controls

| Threat | Current control | Remaining work |
| --- | --- | --- |
| Forged owner/tenant | Hosted schemas reject caller owner/tenant; verified token derives principal | Repeat adversarial test on every release SHA |
| OAuth code/token replay | PKCE, short-lived codes/access tokens, refresh rotation, digested ledgers, revocation | Client-specific expiry/revoke acceptance |
| Cross-tenant database access | Transaction tenant context, owner-scoped services, RLS-oriented schema and composite constraints | Independent production review and continuous regression |
| Token, email, or memory leak | Payload-free logging contract, generic errors, redacted evidence policy | Automated Cloud Logging/artifact canary scan per release |
| Ciphertext swap or key failure | Tenant/record binding and KMS-backed hosted path | Release-SHA swap/rotation/failure/restore exercise |
| Malicious memory prompt injection | Retrieved memory is data, not instructions; bounded MCP tools/scopes | More client-side prompt-injection conformance cases |
| Unauthorized destructive action | `memory:delete` scope, explicit tool approval, idempotency | Portal forget confirmation and audit receipt |
| Deleted data resurrected by restore | Recovery/tombstone design and hosted drills exist | Formal retention and release restore acceptance |
| Abuse or expensive search | Input/result limits | Edge quotas, rate limits, SLOs, alerts, and cost controls |
| Privileged operator abuse | Separate cloud identities and audit design | Access review, break-glass exercise, operational policy |

## Residual risk and no-go conditions

UMCP v1 is server-decryptable. There is no E2EE or zero-knowledge claim.
Production/public-beta promotion is blocked by any demonstrated OAuth bypass,
cross-owner access, RLS bypass, plaintext fallback, sensitive logging,
unbounded abuse path, or restore that makes forgotten data available again.
