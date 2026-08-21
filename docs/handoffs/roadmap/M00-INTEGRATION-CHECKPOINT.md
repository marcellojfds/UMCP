# M00 integration checkpoint

**Status:** partial merge; milestone remains open
**Branch:** `roadmap/integration`
**Worktree:** `/private/tmp/umcp-roadmap-integration`
**Pre-merge baseline:** `325faf32544e17c896ace07b8c712508c3ed7cce`
**Merged lane:** `roadmap/luna-core` through Core implementation `7d798cb` and
handoff `2b22671`

## Current state

The Core G00 capability, demo, current gates and handoff were merged with
`--no-ff` to preserve history. The integration branch is clean after this
checkpoint. This is not `M00-INTEGRATED` and does not permit the next
milestone.

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
