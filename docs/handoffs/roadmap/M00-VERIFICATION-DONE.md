# M00 — Verification handoff

Status: `complete-with-external-findings`

This is the Luna C Verification handoff for G00/M00. It is evidence for the
Verification lane only, not an integrated acceptance or release `GO`.

## Scope and candidate

- Worktree: `/private/tmp/umcp-roadmap-verification`
- Branch: `roadmap/luna-verification`
- Executable SHA tested: `03263d1eafbba494757506aa7e1af7864d2dfbd4`
- Documentation/evidence commit: `e7bf14ce30a3ff78a7ec799b75fc2f10729104a2`
- Baseline: `325faf32544e17c896ace07b8c712508c3ed7cce`
- Data boundary: synthetic/disposable only; no holdout, real data, email,
  paid service, push, PR, deploy or release action.

## Capability → acceptance → demo

Capability: Verification can run independent, fail-closed controls and a
black-box synthetic cross-client memory journey without changing Core or
Experience implementation.

Acceptance:

```sh
pytest -q tests/conformance tests/verification tests/evals/test_development_suites.py
```

Result: `12 passed`.

Demo:

```sh
scripts/demo-local-integration
scripts/demo-cross-client-memory
```

Both passed with synthetic-only output. The cross-client fixture asserts
candidate → confirmation → Claude recall, provenance/source/space, tenant-B
zero, ChatGPT revocation, Claude continuity, forget and tombstone-safe restore.

This is fixture-backed evidence. The Core-backed M00 integration demo remains
`not-run` until the controlled integration branch publishes
`M00-INTEGRATED.md`.

## Current gate freshness

See [`GATE-FRESHNESS.json`](GATE-FRESHNESS.json). Current executable evidence
was rerun on `03263d1` after adding the integration readiness gate.

| Gate | SHA | Freshness | Result | Artifact |
| --- | --- | --- | --- | --- |
| gate-fast | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | current | pass, 73 tests | `evidence/gate-fast.log` |
| PostgreSQL/migrations | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | current | pass, 19 tests | `evidence/postgres-migrations.md` |
| MCP stdio/fixture conformance | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | current | pass | `evidence/conformance-and-evals.log` |
| SDK | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | current | pass, 2 tests | `evidence/sdk-web.log` |
| Web | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | current | check/test/build pass | `evidence/sdk-web.log` |
| dependency/SBOM/secret-PII/claims | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | current | pass | `evidence/` |
| browser E2E | `45ca25c15fedfd383eb96f8a04141fbe2423d3d1` | environment-blocked | no backend | `evidence/browser-preflight.json` |
| Integration readiness | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | current | not-run/WAITING | `evidence/sync-readiness.log` |
| Core-backed M00 acceptance | `03263d1eafbba494757506aa7e1af7864d2dfbd4` | not-run | waiting | no `M00-INTEGRATED.md` |

Historical gates remain historical and are not promoted here.

## Development evals

English and Portuguese protocols are separate development-only suites with 20
cases each, covering capture precision, deduplication, contradiction,
cross-space relevance, provenance, abstention, memory poisoning, prompt
injection, stale memory and concepts. E5, threshold `0.76` and holdout state
were not changed or evaluated by this harness.

## Findings and blockers

- [`M0-ENV-001.md`](findings/M0-ENV-001.md): managed browser runtime has no
  connected backend; browser E2E remains environment-blocked.
- The integration checkpoint reports that this exact `M00-VERIFICATION-DONE.md`
  was previously missing; it is now published on the Verification branch.
- No implementation finding is asserted against Core or Experience because no
  integrated candidate was delivered to this worktree.

## Artifacts and checksums

All committed evidence is under [`evidence/`](evidence/) and verified by
[`checksums.sha256`](evidence/checksums.sha256).

## Technical recommendation and synchronization

Merge this handoff through the controlled integration process only after the
integration owner inspects the branch and resolves any intentional script
ownership conflict. Rerun the Core-backed M00 demo and all affected gates on
the resulting integrated SHA, then create:

```text
docs/handoffs/roadmap/M00-INTEGRATED.md
```

Do not open M01 or issue a release `GO` before that handoff exists.
