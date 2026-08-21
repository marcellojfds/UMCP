# Autonomous Codex coordination

The coordination system has three layers:

1. Git handoffs and tested SHAs are the source of truth.
2. A shared Markdown board is the human-readable, append-only event mural.
3. A Codex heartbeat validates events and dispatches the next existing task.

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
- Use one idempotent `DISPATCHED` event before sending the follow-up task.
- Do not wake a task that is already active.
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
