# Threat model — UMCP Cloud v1 design

**Status:** design baseline, not evidence of implementation (2026-08-21).

## Boundaries and assets

```text
untrusted MCP client -> HTTPS gateway -> verified Principal -> core -> PostgreSQL/RLS
                                                       \-> signed queue -> worker
KMS/secret manager <----------------------------------------^       |
backup/export/audit sinks <-----------------------------------------+
```

Assets are memory content, provenance, embeddings, tenant membership, tokens,
PATs, consent, DEKs, encrypted exports, tombstones, audit events and backups.
Trust boundaries are client/gateway, gateway/core, core/database, worker/queue,
service/KMS, and service/backup sink. The privileged operator can access the
server in v1 and is an explicitly modeled threat.

## STRIDE and abuse cases

| Threat | Mandatory control | Verification gate |
| --- | --- | --- |
| spoofed token, tenant or `owner_id` | verified issuer/signature/audience/expiry; principal-derived tenant; reject hosted owner field | invalid-token and cross-tenant suite |
| token/PAT replay or theft | PKCE, short token expiry, refresh rotation, hash-only PAT, revocation, nonce/idempotency | replay/revocation tests and log scan |
| cross-tenant SQL or worker tampering | transaction tenant context, FORCE RLS, composite FKs, signed envelope | repository and job adversarial tests |
| ciphertext swapping or stale key use | AEAD AAD tenant/record/key binding; versioned key resolver | swap/rotation/KMS failure tests |
| destructive operation repudiation | principal/credential/request/action audit record without payload | audit completeness test |
| memory, email or bearer leak | allowlist telemetry, redaction, generic errors, no payload in audit | canary log/trace/artifact scans |
| queue flood, expensive search, stream disconnect | quotas, limits, rate limiting, cancellation, bounded retry/DLQ | load and backpressure tests |
| forget racing export/re-embed/restore | durable tombstone, transactional state machine, deletion replay before service | concurrent delete and restore tests |
| malicious memory prompt injection | memory treated as untrusted retrieved data; tool schema/scope checks | integration fixtures |
| privileged break-glass abuse | separate role, justification, TTL and alert/audit | access-review exercise |

## Residual risk and no-go

Server-decryptable processing means privileged server access remains material.
There is no E2EE/zero-knowledge claim. Any bypass of RLS, unsigned worker
execution, KMS plaintext fallback, raw sensitive data in logs, or restore that
resurrects deleted data is P0 and blocks release.
