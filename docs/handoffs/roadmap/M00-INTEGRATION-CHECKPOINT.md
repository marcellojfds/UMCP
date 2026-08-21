# M00 integration checkpoint

**Status:** partial merge; milestone remains open
**Branch:** `roadmap/integration`
**Worktree:** `/private/tmp/umcp-roadmap-integration`
**Pre-merge baseline:** `325faf32544e17c896ace07b8c712508c3ed7cce`
**Merged lane:** `roadmap/luna-core` through Core implementation `1eb157f` and
handoff `c0418df`
**Partial demo SHA:** `61705c92215db0547e90e3d668c6fc971574612d`
**Checkpoint commit:** recorded after the partial demo

## Current state

The Core G00 capability, demo, current gates and handoff were merged with
`--no-ff` to preserve history. The integration branch is clean after this
checkpoint. This is not `M00-INTEGRATED` and does not permit the next
milestone.

The reusable demo was exercised in this partial integration context:

```sh
./scripts/demo-local-integration roadmap/integration /private/tmp/umcp-roadmap-integration
```

Result: 4 MCP contract tests and 2 HTTP/auth tests passed. This is partial
evidence only; it is not the final integrated gate until the other applicable
handoffs are merged and all current gates are rerun on the resulting SHA.

Additional partial gates executed on `26d02135d47af5536c12528a6db1638d3083e724`
(the clean integration SHA before the demo-context-only revision):

- `./scripts/gate-fast`: 73 passed, 1 deprecation warning;
- `./scripts/gate-postgres`: 19 passed, PostgreSQL 16.15 + pgvector 0.8.6,
  migrations zero→head and downgrade/re-upgrade passed.

These results are current for the tested integration code paths, but remain
partial until Experience and Verification handoffs are merged.

## Missing applicable handoffs

These files were inspected with `git show` and do not exist yet:

- `roadmap/luna-experience:docs/handoffs/roadmap/M00-EXPERIENCE-DONE.md`
- `roadmap/luna-verification:docs/handoffs/roadmap/M00-VERIFICATION-DONE.md`

Until both lanes publish their handoffs, integration must not claim the full
M00 gate, run a final integrated demo, or open M01/G02. No files were edited in
the Experience or Verification worktrees.

## Freshness boundary

The Core handoff contains current evidence for its own SHA. The merge commit
does not itself constitute a fresh integrated gate. After the missing handoffs
arrive, the integration owner must validate branch/SHA/worktree, merge both
lanes, resolve by intent, rerun the acceptance demo and all applicable current
gates, then create `M00-INTEGRATED.md`.

No release `GO` is issued.
