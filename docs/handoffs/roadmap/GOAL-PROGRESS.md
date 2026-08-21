# Verification lane — goal progress

## Milestone V0 — execution controls and independent fixture harness

- **Outcome:** a Verification executor can prove its own worktree context,
  capability preflight, gate freshness and stagnation policy, then run a single
  synthetic demo with a non-zero failure code.
- **Acceptance command:** `scripts/demo-cross-client-memory`.
- **Paths owned by this lane:** `scripts/`, `tests/conformance/`,
  `tests/verification/`, `evals/development/`, `docs/runbooks/`, and
  `docs/handoffs/roadmap/`.
- **Dependencies:** baseline `325faf32544e17c896ace07b8c712508c3ed7cce`;
  implementation candidates are consumed only after an `M<id>-INTEGRATED.md`
  handoff appears on `roadmap/integration`.
- **Gate:** control scripts and fixture-backed conformance pass; no claim is
  made about Core, Experience, hosted infrastructure, or release readiness.
- **Rollback:** remove only the Verification-owned files in this milestone;
  never revert or edit another lane's implementation.
- **Out of scope:** holdout, E5/threshold changes, source implementation,
  migrations, apps/web, SDK implementation, auth/crypto/RLS changes, deploy,
  push/PR/release and any external service.

## Evidence heartbeat

| Checkpoint | Evidence | Status | Next action |
| --- | --- | --- | --- |
| Contract frozen | This file at the baseline SHA | current | Add controls and fixture harness |
| Capability preflight | `evidence/capability-preflight.json` | current | Browser backend remains environment-blocked |
| Cross-client fixture | `scripts/demo-cross-client-memory` + 12 focused tests | current | Preserve assertions while waiting for Core candidate |
| Core integration | No `M1-INTEGRATED.md` observed | not-run | Wait for integration handoff; continue independent checks |

## Final V0/V1 checkpoint

- **Tested executable SHA:** `45ca25c15fedfd383eb96f8a04141fbe2423d3d1`.
- **Current:** gate-fast 73 passed; PostgreSQL/migrations 19 passed on
  PostgreSQL 16.15 + pgvector 0.8.6; SDK 2 passed; web check/test/build
  passed; dependency audit, secret/PII, SBOM and local links/claims passed.
- **Fixture-only current:** cross-client acceptance and 40 development eval
  cases (20 English + 20 Portuguese) passed. This is not Core evidence.
- **Environment-blocked:** managed browser runtime has no connected backend;
  no browser E2E pass is claimed.
- **Synchronization blocker:** no `M1-INTEGRATED.md` was present on
  `roadmap/integration`; the Core/Experience candidate acceptance remains
  not-run.
- **M00 synchronization:** `roadmap/integration` has now published the
  partial checkpoint and is waiting for the exact
  `M00-VERIFICATION-DONE.md`; this handoff is now present on this branch.
- **Prohibitions honored:** holdout not run, E5/threshold unchanged, no
  external service or real data, no push/PR/deploy/release/GO.

## Classification policy

Every gate is classified as exactly one of `current`, `historical`, `not-run`,
or `environment-blocked`. A historical green result is never promoted to
current after an affected path changes. Environment blockers record the
smallest smoke, observed limitation, and a safe fallback.

## Stagnation response

The detector in `scripts/detect-stagnation` implements the playbook thresholds.
If it exits 1, feature work stops, the smallest reproducer is preserved, one of
three safe alternatives is tried, and the milestone contract is updated before
resuming.
