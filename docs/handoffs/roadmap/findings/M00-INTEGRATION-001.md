# Finding M00-INTEGRATION-001 — integration checkpoint is stale

Status: `external-owner`

Owner lane: `Integration`

## Reproduction

- Worktree/branch/SHA: `/private/tmp/umcp-roadmap-verification`,
  `roadmap/luna-verification`,
  `4d22842fd3392e4bace4e430bdb6245722086e19`
- Command: `scripts/assert-m00-branch-handoffs`
- Expected: the coordination proof identifies the current Core, Experience and
  Verification handoffs and reports only the missing integrated handoff.
- Observed: Core, Experience and Verification handoffs are present on their
  refs, but `roadmap/integration` still lacks
  `docs/handoffs/roadmap/M00-INTEGRATED.md`. Its checkpoint also records those
  three handoffs as missing, which predates the current ref state.

Current source refs inspected:

| Ref | Tip | Handoff |
| --- | --- | --- |
| `roadmap/luna-core` | `164d84b77e74e37d63f42dfc99ae26df1f83765c` | present |
| `roadmap/luna-experience` | `64a9181f870e01d01f6dbb3229cb32086cd0f46` | present |
| `roadmap/luna-verification` | `4d22842fd3392e4bace4e430bdb6245722086e19` | present |
| `roadmap/integration` | `2aa16c3eec9d0126295ccdd0b38405c5ff9fd263` | `M00-INTEGRATED.md` missing |

## Impact and contract

- Affected requirement: controlled M00 synchronization and integrated-candidate
  readiness.
- Severity rationale: coordination evidence is stale and the integrated
  acceptance has not been run; Verification correctly remains waiting.
- Does this affect a release claim? `yes` — no integrated M00 claim or release
  recommendation can be made.

## Evidence

| Artifact | SHA-256 | Freshness |
| --- | --- | --- |
| `evidence/m00-branch-handoffs.log` | recorded in `evidence/checksums.sha256` | current at tested SHA |
| `roadmap/integration:docs/handoffs/roadmap/M00-INTEGRATION-CHECKPOINT.md` | ref content inspected | historical/stale relative to source refs |

## Request to lane owner

Inspect the three current lane refs, merge the applicable handoffs through the
controlled integration process, rerun the integrated acceptance/demo and all
affected current gates, then publish `docs/handoffs/roadmap/M00-INTEGRATED.md`.
Do not treat the partial checkpoint as integrated acceptance.
