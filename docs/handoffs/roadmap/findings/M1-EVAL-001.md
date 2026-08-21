# Finding M1-EVAL-001 — frozen E5 prefix contract mismatch

Status: `external-owner`

Owner lane: `Core`

## Reproduction

- Worktree/branch/SHA: `/private/tmp/umcp-roadmap-verification`,
  `roadmap/luna-verification`,
  `cd7b3a045d158b7b4e6b503e803aeddba8b9e65c`
- Command: `pytest -q` from a clean worktree.
- Expected: the versioned semantic E5 configuration and its ADR-0008 frozen
  promotion configuration satisfy the conformance assertions.
- Observed: two tests fail because the loaded values are `"query: "` and
  `"passage: "` (trailing spaces), while the assertions require `"query:"` and
  `"passage:"`.

Affected assertions:

- `tests/evals/test_semantic_harness.py::test_semantic_configs_are_versioned_and_development_threshold_is_frozen`
- `tests/evals/test_semantic_harness.py::test_e5_promotion_configuration_is_frozen_by_adr_0008`

The same run produced 95 passed, 4 failed and 19 skipped; the other two
failures are the previously recorded loopback HTTP MCP environment blocker.

## Impact and contract

- Affected contract/ADR/threat requirement: E5 semantic configuration
  conformance and ADR-0008 frozen promotion assertions.
- Severity rationale: the frozen candidate is not silently normalized or
  changed by Verification; the mismatch prevents a clean root-suite result.
- Does this affect a release claim? `yes` — E5 configuration conformance is
  not independently green.

## Evidence

| Artifact | SHA-256 | Freshness |
| --- | --- | --- |
| `evidence/full-pytest.log` | recorded in `evidence/checksums.sha256` | current at tested SHA |
| `evals/configs/semantic-e5-small-v2.yaml` | source at tested SHA | current |
| `evals/configs/semantic-e5-small-v2-promotion.yaml` | source at tested SHA | current/frozen |

## Request to lane owner

Resolve the intended prefix contract in the owning implementation/test
boundary without changing the frozen E5 model revision, thresholds or holdout
state. Rerun the full root suite and preserve the exact frozen values in the
resulting evidence.
