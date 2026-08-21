# Luna — Waves 5/6 handoff

**Base SHA:** `2c94d5562368c14224c073a907d35c85063f7c0e`  
**Branch:** `product/luna-experience`  
**Scope:** Waves 5 and 6 experience/ecosystem work only  
**Status:** implementation-ready preview; not a P5/P6 `GO`

## Paths changed

- `apps/web/`: dependency-free, responsive landing/login shell and the
  server-injected administrative-adapter boundary.
- `docs/site/`: public claim gate, Cloud onboarding contract, dated
  compatibility matrix, and surface-specific recipes.
- `packages/sdk-typescript/`: experimental transport-agnostic SDK facade and
  Node tests.
- `examples/conformance/`: provider-neutral lifecycle runner and synthetic
  prompt collection.

## Decisions and contracts consumed

The work consumes ADRs 0010, 0011, 0013, and 0015 plus
`docs/contracts/cloud-principal-and-jobs-v1.md`. The web shell does not access
PostgreSQL, construct principals, retain tokens, accept `owner_id`, or
implement a second authorization model. A server must inject
`window.__UMCP_ADMIN_ADAPTER__` only after it verifies the session. The adapter
derives identity and tenant from the server session; it is the single intended
integration seam for memories, connections/revocation, export, deletion, and
the passwordless-email request.

The TypeScript SDK likewise requires an already-authenticated MCP transport.
It rejects `owner_id` in hosted inputs and requires idempotency keys for write,
update, and forget.

## Verification

- `npm test` in `packages/sdk-typescript`: 2 passed.
- `npm run check` in `apps/web`: passed.
- `node --check examples/conformance/runner.mjs`: passed.
- `./scripts/gate-fast`: 47 passed; one pre-existing Starlette/httpx
  deprecation warning.
- `git diff --check`: passed.

Selected artifact SHA-256 values:

```text
5587f22822dd6cafca40084a0f97f0a4546887226506a0041230dd18bb60fb15  apps/web/index.html
d284607737aa9ac40c2f36246b8205f01fe5948324cf3982e9a0824886d263d2  apps/web/src/app.js
5112e7d36c7dff6ac6dd0f2c273a70a5b65c801cca0fd94e9b74926ace3013c7  docs/site/compatibility-matrix.md
688fc39eec83ecc424304900d90793cc4213546a151cb9c63c7721c8f393bbf8  packages/sdk-typescript/src/client.js
8234f13c0faccf00d5e3bb6cdb172ad4c0006821da31b72f02e82c5fac3ed3f7  examples/conformance/runner.mjs
```

## Deliberate skips and remaining gates

- No real email, Cloud deployment, external client integration, publishing,
  holdout, remote Git operation, or paid service was used.
- No admin API, verified email callback, OAuth flow, dashboard data endpoint,
  connection/revocation endpoint, export/deletion endpoint, or remote `/mcp`
  gateway exists in this worktree. Therefore the login remains unavailable by
  default and all remote client rows are **Unverified**. This is intentional,
  not a simulated auth flow.
- No claim is enabled for encryption in transit/at rest, per-tenant keys,
  E2EE, zero knowledge, or universal compatibility.
- Playwright E2E, visual snapshots, CSP/security-header, authenticated
  cross-tenant, auth replay, actual revocation, and real lifecycle tests await
  Terra's published server adapters and an authorized staging environment.

## Terra integration request

Publish a versioned administrative API adapter with server-rendered bootstrap
and capability metadata for: magic-link request/callback, session state,
paginated memory explorer, connection scopes/revocation, export request/status,
account deletion request/status, and audit-safe operation receipts. It must
enforce the principal contract, CSRF/session protections, scope checks,
idempotency, tenant isolation, and safe errors. Once available, Luna can wire
the shell, add authenticated E2E coverage, and execute client conformance
against an authorized environment.

## Authorization still needed

Deployment/staging, email sending, external client testing, dependencies for
browser E2E, and any publication remain separately unauthorized.
