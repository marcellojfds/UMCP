# P01 — Terra contracts and architecture handoff

**Branch/SHA-base:** `terra-alpha-recovery` / `4947ebfb3789558892c242e0d7a8743256f3656d`
**Wave:** 1 — contracts and ADRs
**Status:** design completed locally; implementation has not started.

## Paths added

- `docs/adr/0009-community-and-cloud-editions.md` through
  `docs/adr/0015-umcp-brand-and-compatibility.md`;
- `docs/contracts/cloud-principal-and-jobs-v1.md`;
- `docs/contracts/cloud-migration-plan-v1.md`;
- `docs/threat-model-hosted-v1.md`.

## Decisions and contracts available to Luna

The accepted local ADR baseline fixes one core with two compositions, `/mcp`
for remote Streamable HTTP, verified-principal-only Cloud access, shared
PostgreSQL FORCE RLS, server-decryptable envelope encryption, frozen E5
retrieval configuration, and compatibility claims by tested surface.

`cloud-principal-and-jobs-v1` is the shared contract: hosted tool arguments do
not contain `owner_id`; the gateway creates `Principal`; workers accept signed
tenant-bound envelopes. Luna must not implement a second authorization path.

## Commands and results

- verified 14 report checksum manifests: all declared hashes matched;
- `git diff --check`: pass;
- `./scripts/scan-ci-safety`: pass;
- `./scripts/gate-fast`: pass (47 tests; one existing deprecation warning);
- no holdout, dependency/model download, stage/commit/push/PR/tag/release,
  remote mutation, KMS or identity-provider action was performed.

## Migration/recovery policy

The forward-only, additive migration and restore/tombstone rule is in
`cloud-migration-plan-v1`. Production downgrade is prohibited; use forward fix
or verified restore.

## Claims

No new product claims are enabled. E2EE, zero knowledge, operator
inaccessibility, per-tenant encrypted content, Cloud compatibility and release
readiness remain prohibited until their stated implementation and test gates.

## Remaining authorizations and risks

P00 remains blocked from a clean SHA by absent exact-path staging/local-commit
authorization. Also required are provider/KMS/queue selection and any
dependency or service acquisition, isolated Terra/Luna worktrees, and all
external/holdout/release approvals. Hosted STRIDE risks and P0 no-go criteria
are recorded in `docs/threat-model-hosted-v1.md`.
