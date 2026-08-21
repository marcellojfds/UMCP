# Terra — data-plane handoff

**Branch:** `product/integration`
**Implementation base:** `1eff255`
**Status:** local implementation and verification complete; not a production or release `GO`.

## Delivered locally

- Official MCP Streamable HTTP at `/mcp`, with separate health/readiness,
  authenticated principals, hosted-schema owner rejection and tenant-local rate
  limits.
- PostgreSQL Cloud composition with FORCE RLS, transaction-scoped tenant
  context, adversarial cross-tenant coverage and additive migrations through
  `0006_cloud_envelope_storage`.
- Server-decryptable envelope storage for memory content and provenance,
  versioned rewrap for current and historical records, and an explicit local
  KMS adapter. Vectors remain sensitive queryable data under RLS/storage
  encryption; they are not application-envelope encrypted.
- Local administrative API and captured-mailbox authentication seam, CSRF,
  PAT expiry/revocation, and same-origin web bootstrap.
- Durable Cloud PostgreSQL tombstones written transactionally with `forget`,
  plus audit events for successful write/update/forget operations. Audit events
  carry structural metadata only, never memory payload, provenance, owner ID,
  token or ciphertext.

## Evidence

- `./scripts/gate-fast`: **67 passed** (one Starlette/httpx deprecation warning).
- `./scripts/gate-postgres`: **18 passed**, including disposable PostgreSQL 16
  + pgvector, zero-to-head migrations and downgrade/re-upgrade validation.
- TypeScript SDK test: **2 passed**; web syntax check and conformance syntax
  check passed.
- Dependency audit: no known vulnerabilities; CI safety scan passed.
- The final candidate's SBOM is generated locally after its documentation
  commit, using its Git SHA in the artifact filename.

## Recent local commits

- `e9f0330 feat: persist cloud deletion tombstones`
- `1eff255 feat: audit cloud memory mutations`

## External-authorization boundary

Production IdP/JWKS, KMS/HSM, email delivery, queue/worker infrastructure,
encrypted backup transport and restore worker, staging TLS/storage verification,
deployment, publication and any release remain **ready for external
authorization**. No production deployment, real data, remote Git action,
holdout access, E2EE/zero-knowledge claim or release `GO` was performed.
