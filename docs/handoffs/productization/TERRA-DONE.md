# Terra — data-plane handoff

**Branch:** `product/integration`
**Implementation base:** `e753829`
**Status:** local implementation and verification complete; not a production or release `GO`.

## Delivered locally

- Official MCP Streamable HTTP at `/mcp`, with separate health/readiness,
  authenticated principals, hosted-schema owner rejection and tenant-local rate
  limits.
- PostgreSQL Cloud composition with FORCE RLS, transaction-scoped tenant
  context, adversarial cross-tenant coverage and additive migrations through
  `0007_tenant_fks`, including composite FKs that bind memory children to the
  parent tenant.
- Server-decryptable envelope storage for memory content and provenance,
  versioned rewrap for current and historical records, and an explicit local
  KMS adapter. Vectors remain sensitive queryable data under RLS/storage
  encryption; they are not application-envelope encrypted.
- Local administrative API and captured-mailbox authentication seam, CSRF,
  PAT expiry/revocation, stable local re-login identity, safe scope errors,
  account-deletion revocation, and same-origin web bootstrap.
- Durable Cloud PostgreSQL tombstones written transactionally with `forget`,
  plus audit events for successful write/update/forget operations. Audit events
  carry structural metadata only, never memory payload, provenance, owner ID,
  token or ciphertext.

## Evidence

- `./scripts/gate-fast`: **71 passed** (one Starlette/httpx deprecation warning).
- `./scripts/gate-postgres`: **18 passed**, including disposable PostgreSQL 16
  + pgvector, zero-to-head migrations and downgrade/re-upgrade validation.
- TypeScript SDK test: **2 passed**; web tests **3 passed**, check, build and
  conformance syntax check passed.
- Dependency audit: no known vulnerabilities; CI safety scan passed.
- The final candidate's SBOM is generated locally after its documentation
  commit, using its Git SHA in the artifact filename.

## Recent local commits

- `e9f0330 feat: persist cloud deletion tombstones`
- `1eff255 feat: audit cloud memory mutations`
- `9b25a63 feat: execute local account deletion workflow`
- `6e99570 fix: revoke local tenant access on deletion`
- `e753829 feat: enforce tenant scoped memory foreign keys`

## External-authorization boundary

Production IdP/JWKS, KMS/HSM, email delivery, queue/worker infrastructure,
encrypted backup transport and restore worker, staging TLS/storage verification,
deployment, publication and any release remain **ready for external
authorization**. No production deployment, real data, remote Git action,
holdout access, E2EE/zero-knowledge claim or release `GO` was performed.

The local Admin control plane and worker are explicitly in-memory development
adapters; they are not durable hosted services. Browser E2E at desktop/390px,
keyboard and visual-snapshot coverage also remains unverified.
