# UMCP manager protocol

## State model

Maintain `coordination/ROADMAP-MANAGER.md` as a compact append-only log plus a
small current-state block. It is coordination metadata, not acceptance proof.

The current-state block records `manager_status`, canonical ref, active task,
cursor, cadence, run contract, progress time, recovery count and reconciled SHA.
Append events only for dispatch, reconciliation, remediation, repair, audit,
stall, decision-needed, stopped and complete; do not append unchanged polls.

## Bootstrap and selection

Resolve a manual or deadline run contract before dispatch. Preserve the primary
dirty worktree. Parse the committed checklist using `roadmap_state.py` at the
canonical SHA, verify every checked-but-unreconciled item, then create one
heartbeat and one project-worktree executor. Select only dependency-ready,
unchecked items with authorized checkpoints and non-overlapping paths.

## Dispatch contract

Every executor starts from the exact canonical ref, reads the item and previous
handoff, uses synthetic data, freezes its acceptance test, makes only owned
changes, writes `docs/handoffs/roadmap/<ID>-DONE.md`, checks only its own item,
commits local work and ends clean. It must not push, deploy, use credentials,
real users/data or external services without explicit scoped authorization.

## Heartbeats and reconciliation

At each heartbeat first enforce the deadline, take a compact task snapshot,
reconcile only completed or attention-needed tasks, then dispatch at most one
successor. A final message is only a lead: verify final SHA ancestry, handoff,
checkbox, clean tree, current acceptance evidence, honest skips and owned paths.
Advance the canonical ref only after validation. Do not require a handoff to
contain the SHA of the commit that contains that handoff.

## Failures, checkpoints and stopping

For a failed reconciliation: one focused remediation on the same executor,
then a bounded repair, then one independent audit where safe. Retain the
heartbeat through recoverable stalls. Checkpoint approval must be explicit and
scoped; never infer provider, budget, credential, deployment or IAM decisions.

At an explicit stop or deadline, do not dispatch new work; snapshot any active
executor without interrupting it, persist resumable state, mark the manager
stopped and delete the heartbeat. Do not merge, push, tag, release, deploy or
publish merely because local delivery is complete.
