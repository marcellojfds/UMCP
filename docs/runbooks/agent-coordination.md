# Autonomous Codex coordination

The coordination system has three layers:

1. Git handoffs and tested SHAs are the source of truth.
2. A shared Markdown board is the human-readable, append-only event mural.
3. A Codex heartbeat validates events and creates a fresh task for the next
   bounded phase.

The runtime board for this workstation is:

```text
/Users/marcellojunqueirafranco/Documents/UMCP/coordination/AGENT-BOARD.md
```

All writers must call the integration-owned helper. Direct concurrent edits are
not allowed.

```sh
/private/tmp/umcp-roadmap-integration/scripts/agent-board \
  --board /Users/marcellojunqueirafranco/Documents/UMCP/coordination/AGENT-BOARD.md \
  publish \
  --event-id M01-core-done-<sha> \
  --milestone M01 \
  --lane core \
  --agent luna-a \
  --status DONE \
  --sha <tested-sha> \
  --evidence docs/handoffs/roadmap/M01-CORE-DONE.md \
  --message "Core contract and acceptance evidence published"
```

The helper uses an exclusive file lock, append-only events and stable event IDs.
Replaying an identical event is safe; reusing an ID with different content fails.

## Dispatch policy

- Never dispatch from free-form prose alone.
- Resolve the evidence against the stated Git branch and inspect its contents.
- Confirm the worktree/branch/SHA and required predecessor handoff.
- Publish `CLAIMED` before task creation and `DISPATCHED` with the created task
  id after creation. Publish `FAILED` if setup or creation fails.
- Do not send follow-ups to the legacy persistent terminal tasks. An interactive
  terminal remains the active writer even after its goal reports achieved,
  stalled or blocked, so an app-side follow-up can be rejected as
  `active writer`.
- Create one fresh Codex task and one unique `codex/<phase>-<attempt>` branch
  for each bounded phase. Never create a second task for a phase that already
  has a live or successfully dispatched task.
- Monitor created tasks by task id. A completed task must still be reconciled
  against its branch, handoff and tested SHA before downstream dispatch.
- A lane `DONE` may wake Verification or Integration only when its declared
  contract and handoff exist. `INTEGRATED` opens the next milestone contract;
  it is not a release GO.
- `BLOCKED` wakes the dependency owner only when the blocker identifies a
  concrete missing handoff owned by that lane.
- Holdout, push, PR, deployment, paid services, real data and release claims
  remain outside this local coordinator's authority.

## Recovery

The board is a notification ledger, not product evidence. If it is lost, rebuild
it from Git refs and handoffs. If a dispatch fails, publish a `FAILED` event and
retry with the same logical dispatch key only after the failure is understood.

## Current recovery boundary

The independent post-integration audit at
`roadmap/luna-verification:docs/handoffs/roadmap/M00-POST-INTEGRATION-VERIFICATION.md`
returned `M01_NOT_READY`. The required order is therefore:

1. remediate the two stale pre-integration synchronization assertions;
2. test the coordination commit and remediation on one clean pinned SHA;
3. run a fresh independent M00 readiness verification task;
4. open M01 only after that handoff explicitly recommends readiness.

Browser and dependency checks may remain `environment-blocked` when accurately
classified; they must never be silently converted to passes.
