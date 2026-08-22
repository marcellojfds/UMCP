# Roadmap M00 lane progress

## Experience lane — M00 / G00 baseline audit

- Outcome: branch-scoped Experience baseline audited and documented.
- Delivered source baseline: `325faf32544e17c896ace07b8c712508c3ed7cce`.
- Acceptance: web check/unit/build pass; TypeScript SDK tests pass; root suite
  partial with loopback and E5 findings recorded in the Experience handoff.
- Browser E2E: not run.
- Scope boundary: no backend endpoint, hosted, production or release claim.
- Integrated commit: `d3730f8` only; later Experience preview commits are
  intentionally excluded from M00.

## Verification lane — M00 execution controls and independent evidence

- Outcome: fail-closed controls, gate freshness evidence and a synthetic
  fixture-backed cross-client harness are available for independent review.
- Acceptance: `pytest -q tests/conformance tests/verification tests/evals/test_development_suites.py`
  was recorded as 12 passed on the Verification lane.
- Fixture-only cross-client evidence is not Core-backed M00 acceptance and does
  not authorize M1, holdout, production or release claims.
- Environment blockers: browser backend and sandbox loopback HTTP binding.
- Integrated commit: frozen Verification SHA `7837d0d`; later branch changes
  remain excluded from M00.
- Finding retained for integration resolution: `M1-EVAL-001` E5 prefix
  assertion/config whitespace mismatch.

## Integration status

- Core handoff is present; Experience and Verification M00 handoffs are
  consumed only through their frozen commits.
- `M00-INTEGRATED.md` remains the required final artifact. Until it exists,
  no next milestone opens and no release `GO` is issued.
- All gates must be classified as `current`, `historical`, `not-run`, or
  `environment-blocked`; fixture-backed M1 evidence remains explicitly
  non-integrated.

## M01 contract freeze — bounded Core Contract

- Outcome: `M01-CORE-CONTRACT.md` freezes the implementable local contract for
  capture candidate → Inbox confirmation → cross-space recall → tenant
  isolation → scoped revocation → forget/tombstone-safe restore.
- Contract SHA: `d5b2513ee0bab426f590ad092cbefcd21a9bc8e8` (documentation is
  being authored from this clean detached baseline; the delivery commit is the
  next local SHA).
- Acceptance: the ten-step synthetic scenario in the contract must run through
  the M1 HTTP MCP boundary; current fixture-only scripts remain historical and
  are not Core acceptance.
- Ownership: M1-A/M1-B Core owns domain, application, migration and MCP
  semantics; M1-C Experience owns Inbox UI; M1 Verification owns black-box
  conformance. No M00 handoff is edited.
- Parallelization: M1-A, M1-C and M1 Verification may be dispatched only after
  the contract file and this heartbeat are committed and the clean SHA is
  consumed by the coordinator.
- Boundary: this is a contract freeze, not M1 implementation, integration,
  release GO or production/hosted approval.
