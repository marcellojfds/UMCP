# M<id> — Verification handoff

Status: `in progress | complete-with-external-findings | blocked-by-environment`

This handoff is verification evidence, not an independent release GO.

## Candidate and acceptance

- Tested worktree: `/private/tmp/umcp-roadmap-verification`
- Branch:
- Delivered SHA:
- Acceptance command:
- Demo command:
- Synthetic-data statement: no real users, secrets, email, paid service or holdout.

## Gate freshness

| Gate | SHA | Freshness | Result | Artifact |
| --- | --- | --- | --- | --- |
| gate-fast | `<sha>` | current/historical/not-run/environment-blocked | pass/fail/not-run/blocked | `<path>` |

## Results

### Current gates

<!-- Commands executed on the candidate SHA. Include exit code and checksum. -->

### Historical gates

<!-- Cite old evidence without promoting it. -->

### Failures and findings

<!-- Link to docs/handoffs/roadmap/findings/<milestone>-<id>.md. -->

### Environment blockers

<!-- Name the smallest smoke, the limitation and the safe fallback. -->

## Artifacts and checksums

| Artifact | SHA-256 | Freshness |
| --- | --- | --- |
| `<path>` | `<sha256>` | current/historical |

## Technical recommendation

State the next technical action and residual risk. Do not issue a release GO.

## Synchronization

- Required integration handoff: `docs/handoffs/roadmap/M<id>-INTEGRATED.md`
- Next candidate SHA to test:
