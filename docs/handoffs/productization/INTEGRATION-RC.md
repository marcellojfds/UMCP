# UMCP local integration RC

**Branch:** `product/integration`
**Implementation base:** `e753829`
**Scope:** locally integrated Terra data-plane and Luna experience work.

## Included histories

- `product/terra-data-plane` and `product/luna-experience` are preserved in
  this branch history.
- Luna handoff: `docs/handoffs/productization/LUNA-DONE.md`.
- Terra handoff: `docs/handoffs/productization/TERRA-DONE.md`.

## Verified local gates

| Check | Result |
| --- | --- |
| Python fast gate | 71 passed |
| PostgreSQL integration/e2e gate | 18 passed |
| TypeScript SDK | 2 passed |
| Web tests / check / build | 3 passed / passed / passed |
| MCP conformance syntax | passed |
| Dependency audit / CI safety scan | passed |

The local browser inspection covered the landing structure only. Browser E2E at
desktop/390px, keyboard and visual-snapshot coverage remain unverified.

## Current architecture and migrations

- `/mcp`, `/admin` and `/web` compose locally on one origin. The web adapter
  uses only the server-owned Admin API and HttpOnly session cookie.
- Cloud PostgreSQL uses transaction tenant context, FORCE RLS, envelope storage
  for content/provenance, tombstones, payload-free audit events and migration
  head `0007_tenant_fks`.
- `0007_tenant_fks` adds composite tenant+memory FKs for versions, both
  embedding stores and relations; an adversarial PostgreSQL test rejects a
  child bound to another tenant.
- Local account deletion removes the owner’s encrypted memories, leaves
  content-free tombstones, and revokes local sessions, connections and PATs.

## Deliberate local-only adapters and risks

- Mailbox links, sessions, connections, credentials, operation receipts and
  worker queue state are in-memory development adapters. They are not durable
  control-plane storage and must not be used as hosted production services.
- Export is an accepted local request, not an encrypted downloadable object.
- Production IdP/JWKS, KMS/HSM, email, queue, backup transport/restore worker,
  TLS/storage evidence and deployment are external-authorization work.

## Honest release boundary

This is a local integration candidate, not a production readiness statement.
It does not claim E2EE, zero knowledge, universal client compatibility,
encrypted backups, staging TLS/storage verification, or a public release.
Those steps require external authorization and provisioned services.
