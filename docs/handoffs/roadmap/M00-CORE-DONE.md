# M00 Core handoff

**Milestone:** M00 / G00 — Integration Recovery
**Branch:** `roadmap/luna-core`
**Worktree:** `/private/tmp/umcp-roadmap-core`
**SHA:** `9efbc9c1ac85aa20a77032af20a3768716e29320`
**Status:** Core lane complete; integration pending other lanes and verification

## Capability

The current Terra/Luna local integration candidate has one reproducible,
synthetic Core demo and refreshed local evidence. It is still a local
integration candidate, not production-ready and not a release `GO`.

## Acceptance and demo

```sh
./scripts/demo-local-integration
```

Result on the SHA above: **pass**. It exercised the existing application/MCP
path for write → search → update → forget, cross-owner isolation, the hosted
owner boundary and fail-closed authentication. It printed no sensitive
payloads and used synthetic data only.

## Changes

- Added `scripts/demo-local-integration` as the single G00 entrypoint.
- Added the G00 contract and evidence heartbeat in `GOAL-PROGRESS.md`.
- Fixed `scripts/gate-postgres` so teardown that leaves the disposable database
  at Alembic `base` is upgraded to `head` before cleanup truncation.
- Preserved the validated integration source and all Terra/Luna histories;
  no `apps/web`, SDK or site files were edited.

## Current gate freshness

| Gate | SHA | Freshness | Result | Artifact/evidence |
| --- | --- | --- | --- | --- |
| worktree/branch/SHA | `9efbc9c` | current | pass, clean | `/private/tmp/umcp-roadmap-core` |
| G00 demo | `9efbc9c` | current | pass | `scripts/demo-local-integration` |
| Ruff/mypy/unit/contract | `9efbc9c` | current | 73 passed, 1 deprecation warning | `./scripts/gate-fast` |
| PostgreSQL/migrations | `9efbc9c` | current | 19 passed; zero→head and downgrade/re-upgrade pass | `./scripts/gate-postgres`, PG 16.15 + pgvector 0.8.6 |
| MCP stdio/HTTP and auth negative | `9efbc9c` | current | pass in demo and contract suite | `tests/contract`, `gate-fast` |
| cross-owner/tenant and encryption paths | `9efbc9c` | current | pass in current unit/PostgreSQL suites | `tests/unit`, `tests/integration`, `gate-postgres` |
| workers | `9efbc9c` | current | covered by current fast suite | `./scripts/gate-fast` |
| TypeScript SDK | `9efbc9c` | current | 2 passed | `npm test --prefix packages/sdk-typescript` |
| Web tests/check/build | `9efbc9c` | current | 3 passed; check/build pass | `npm test/check/build --prefix apps/web` |
| secret/PII and CI safety | `9efbc9c` | current | pass | `scan-ci-safety`; runtime scan on generated `apps/web/dist` |
| SBOM | `9efbc9c` | current | generated | `/private/tmp/umcp-roadmap-core-sbom-9efbc9c.json` |
| dependency audit | `9efbc9c` | environment-blocked | pip bootstrap requires unavailable network | `./scripts/audit-dependencies` |
| browser visual/keyboard/reduced-motion E2E | — | not run | loopback/browser limitation | post-mortem evidence |
| hosted providers, real data, holdout, deploy, release | — | not run | outside authorization | explicit scope boundary |

Historical results in `docs/handoffs/productization/INTEGRATION-RC.md` and the
session post-mortem are preserved as historical; they are not used to promote
the current HEAD beyond the evidence above.

## Integration gate and next action

The Core lane is ready for the controlled M00 integration sequence. Experience
and Verification handoffs are not present on their branches at this point;
the integration owner must inspect them with `git show` before merging. No next
milestone is opened until capability, acceptance, demo, current gates and all
applicable handoffs are present.

Known external/unauthorized work remains: real IdP/JWKS, KMS/HSM, e-mail,
durable queue, backup transport/restore, TLS/deploy, browser E2E infrastructure,
holdout, publication and independent release audit. No `GO` is issued.
