# P00 — Luna ready

**Baseline SHA:** `2c94d5562368c14224c073a907d35c85063f7c0e`
**Luna branch:** `product/luna-experience`
**Luna worktree:** `/private/tmp/umcp-product-luna`
**Verified state:** clean and based exactly on the baseline SHA.

## Contracts available

- `docs/adr/0009-community-and-cloud-editions.md` through ADR 0015;
- `docs/contracts/cloud-principal-and-jobs-v1.md`;
- `docs/contracts/cloud-migration-plan-v1.md`;
- `docs/threat-model-hosted-v1.md`;
- MCP v0 and internal application/repository contracts already under
  `docs/contracts/`.

## Verified baseline checks

The preserved baseline recorded 14 verified eval checksum manifests,
`git diff --check`, `scripts/scan-ci-safety`, and `scripts/gate-fast` (47
passing tests; one pre-existing Starlette/httpx deprecation warning). Holdout
was not opened or run.

## Ownership

Luna may edit `apps/web/`, `docs/site/`, `packages/sdk-typescript/`, client
recipes and compatibility/design documentation. Before these paths exist,
Luna may create them. Changes to `src/omp/`, `migrations/`,
`services/gateway/`, `services/worker/`, `deploy/`, shared contracts, auth,
authorization, cryptography, repository schemas or MCP wire contracts require
an explicit Terra handoff; Luna must not create a second authorization model.

## Remaining prohibitions

No holdout, remote Git operation, PR/tag/release, publication/deploy, paid
service activation, real email, beta opening, real-user data access, or use of
the compromised OpenAI key is authorized.
