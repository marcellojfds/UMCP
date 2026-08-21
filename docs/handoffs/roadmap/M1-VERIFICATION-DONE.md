# M1 — Verification handoff

Status: `complete-with-external-findings`

This handoff records a fixture-backed Verification harness. It is not proof
that Core or Experience implements M1 and it does not issue a release GO.

## Acceptance and demo

- Tested executable SHA: `45ca25c15fedfd383eb96f8a04141fbe2423d3d1`
- Acceptance: `pytest -q tests/conformance tests/verification tests/evals/test_development_suites.py`
- Demo: `scripts/demo-cross-client-memory`
- Fixture result: candidate → confirm → Claude recall, provenance/source/space,
  tenant-B zero, ChatGPT revocation, Claude continuity, forget, and
  tombstone-safe restore all asserted.

The assertions are black-box against `scripts/verification_fixture.py`, a
disposable test fixture. They intentionally do not import or modify Core.

## Current gates

| Gate | SHA | Freshness | Result | Artifact |
| --- | --- | --- | --- | --- |
| fixture cross-client | `45ca25c15fedfd383eb96f8a04141fbe2423d3d1` | current | pass | `evidence/conformance-and-evals.log` |
| development eval EN | `45ca25c15fedfd383eb96f8a04141fbe2423d3d1` | current | pass | `evidence/evals-en.json` |
| development eval PT | `45ca25c15fedfd383eb96f8a04141fbe2423d3d1` | current | pass | `evidence/evals-pt.json` |
| Core-backed M1 acceptance | `45ca25c15fedfd383eb96f8a04141fbe2423d3d1` | not-run | not-run | no `M1-INTEGRATED.md` |
| browser E2E | `45ca25c15fedfd383eb96f8a04141fbe2423d3d1` | environment-blocked | blocked | `evidence/browser-preflight.json` |

## Development suites

English and Portuguese protocols are separate, 20 cases each, and development
only. Categories cover capture precision, deduplication, contradiction,
cross-space relevance, provenance, abstention, memory poisoning, prompt
injection, stale memory and concepts. No model, holdout, threshold or E5
candidate was changed or evaluated by this harness.

## Findings and blockers

- [`M0-ENV-001.md`](findings/M0-ENV-001.md): browser backend unavailable.
- Synchronization is pending `roadmap/integration` publishing
  `docs/handoffs/roadmap/M1-INTEGRATED.md`; Core-backed M1 assertions remain
  not-run.

## Artifacts and recommendation

Checksums are in `evidence/checksums.sha256`. The recommendation is to retain
the harness, rerun it unchanged against the integrated candidate, and ask the
lane owner for the browser environment. No release GO is issued.
