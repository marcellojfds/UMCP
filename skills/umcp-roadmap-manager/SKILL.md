---
name: umcp-roadmap-manager
description: Coordinate the UMCP repository roadmap autonomously for a user-defined run window by reading the Codex roadmap and implementation checklist, dispatching dependency-ready items to cost-efficient Terra or Luna project worktree tasks, recovering from executor failures, reconciling evidence, and reporting incremental progress through a persistent heartbeat. Use when the user asks to run, continue, manage, or babysit the UMCP roadmap for an extended period.
metadata:
  short-description: Coordinate UMCP roadmap work
---

# UMCP Roadmap Manager

Operate one evidence-driven manager task for the UMCP repository. Advance the
canonical implementation line through small Terra/Luna tasks while keeping the
user's primary working tree untouched.

## Sources of truth

Resolve the repository root, then read in this order:

1. `docs/CODEX_DELIVERY_ROADMAP.md`;
2. `docs/roadmap_implementation.md`;
3. `docs/EXECUTION_RELIABILITY_PLAYBOOK.md`;
4. `coordination/ROADMAP-MANAGER.md` if it exists;
5. the handoff for the last completed checklist item.

The implementation checklist between `roadmap-manager:start` and
`roadmap-manager:end` defines IDs, models, dependencies, checkpoints and
completion boxes. Git refs, final SHAs, clean worktrees, handoffs and current
acceptance evidence remain authoritative; a checked box alone is not proof.

## Required protocol

Read [references/manager-protocol.md](references/manager-protocol.md) before
starting or resuming coordination. It defines bootstrap, task prompts,
heartbeat state, reconciliation, failure handling and stopping conditions.

Use [scripts/roadmap_state.py](scripts/roadmap_state.py) to parse the checklist
instead of repeatedly loading the full document. Use `--json` for a compact
machine-readable snapshot and `--git-ref <SHA>` after the canonical line has a
committed implementation document.

## Operating defaults

- Run contract: before dispatch, establish either `until manual stop` or an
  explicit duration/deadline. If the invocation omits this, ask one concise
  question. Never silently invent an unlimited run.
- Coordination cadence: 10 minutes; use 5 minutes only when requested.
- Progress cadence: 30 minutes unless requested otherwise. Also report every
  dispatch, reconciliation, recovery transition, checkpoint and completion.
- Concurrency: one active executor. Increase only when the user explicitly
  requests parallelism and owned paths do not overlap.
- Models: `gpt-5.6-luna` for Luna items and `gpt-5.6-terra` for Terra or audit
  items. Do not use Sol for executor work unless the user asks.
- Reasoning: low for Luna, medium for Terra, high for an explicitly marked
  independent audit when needed.
- Task mechanism: create a project task in a Git worktree from the canonical
  ref. Prefer a fresh task with a bounded prompt over a literal history fork.
- Notifications: keep unchanged coordination polls silent, but send the
  periodic progress bulletin even when the executor is still running.

## Essential invariants

- Dispatch only dependency-ready unchecked items and never duplicate an active item.
- The executor marks its own checklist box only after its gate passes, writes
  `docs/handoffs/roadmap/<ID>-DONE.md`, commits all lane work locally and ends clean.
- Reconcile the final SHA before advancing. The final SHA is verified from Git
  and the task result; never require a commit to contain its own SHA.
- Advance the canonical ref to the reconciled delivery SHA. The next task
  starts from that exact ref, so completed boxes and handoffs travel forward.
- Do not infer authorization for provider changes, deploy, credentials, paid
  services, real email/data/users, holdout, push, PR, tag, release or publication.
- Keep exactly one heartbeat alive through recoverable failures, technical
  stalls and user checkpoints. Delete it only on explicit user stop, the
  configured deadline, or program completion.

## Invocation outcome

When invoked with a run contract, inspect and reconcile state, dispatch the
first safe item, create or update one heartbeat attached to the manager task,
and report the active ID, executor model, canonical base, completion ratio,
what the active delivery will enable, next check and next progress bulletin.
