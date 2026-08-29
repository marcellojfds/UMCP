# UMCP Manager Board — MVP sprint

Updated: 2026-08-29

## Outcome

Put the private controlled MVP in usable condition as quickly as safely
possible. Success means:

1. the hosted MCP can be connected to the owner's ChatGPT and Gemini surfaces;
2. a hosted authentication/account-management screen is available after the
   MCP connection;
3. a conversation/memory born in one supported assistant can be exported or
   transferred through MCP and consumed in another supported assistant;
4. every claim is backed by a clean Git SHA, current acceptance evidence and a
   reconciled handoff.

This sprint does not authorize production, public beta, external users, push,
PR, tag, release, new paid services, or spend beyond an explicitly recorded
checkpoint.

## Sources of truth

- Worktree: `/private/tmp/umcp-pr1`
- Branch: `codex/fix-pr-1`
- Resumption handoff: `docs/handoffs/roadmap/MVP-RESUMPTION-20260829.md`
- Checklist: `docs/roadmap_implementation.md`
- Delivery roadmap: `docs/CODEX_DELIVERY_ROADMAP.md`
- Reliability contract: `docs/EXECUTION_RELIABILITY_PLAYBOOK.md`
- Coordination history: `coordination/ROADMAP-MANAGER.md`
- Notification log: `coordination/AGENT-BOARD.md`

Git handoffs, tested SHAs and current acceptance evidence are authoritative.
Slack is a coordination and notification surface, not proof of delivery.

## Current state

- Progress: 10/43 checklist items complete.
- H07: complete; M2 staging ready on revision
  `umcp-cloud-staging-00018-f78`; not production-ready.
- C01: implementation exists and reported 14/14, but gate is open.
- C02: implementation exists and reported 15/15 with containment 0/0/0, but
  gate is open.
- Shared blocker: the audit image was built before the code was committed, so
  its claimed `audit_source_sha` is not reproducible.
- C03 and all downstream items: blocked by dependencies and/or checkpoints.

## Safety containment — 2026-08-29 14:42 UTC

- All six lane schedulers are `PAUSED` after the independent coordination
  review found no shared lock/CAS, stale `READY` rows and divergent worktree
  bases. The manager heartbeat is active in monitor-only mode.
- The owner authorized one controlled integration/remediation path. W01R1 is
  active in task `01a04e8a-7759-71d0-8b58-7197260aec67`; no second worker may
  be dispatched while it is active.
- W01 delivered a stdlib-only checksum verifier and a locally built clean-SHA
  image, but did not publish or run it in staging. C01/C02 remain open.
- W05 found additional P0 defects that must be repaired before publication:
  declarative image-to-SHA provenance and fail-open job/empty-containment
  handling. Publication authorization alone is not sufficient for acceptance.

## Work protocol

1. A worker may claim only one `READY` item assigned to its lane.
2. Before editing, record base SHA, owned paths and acceptance evidence.
3. Use a dedicated project worktree; never edit the dirty primary checkout.
4. Do not overlap owned paths with another active claim.
5. `DONE` requires a clean worktree, local commit, final SHA, current commands
   and a handoff. A Slack message alone is not delivery.
6. The manager reconciles delivery before opening dependants.
7. A missing permission, credential, checkpoint or product decision yields a
   precise `BLOCKED` event; workers do not infer authorization.
8. When there is no eligible item, exit quietly. Do not manufacture work.

## Worker lanes

| Worker | Model | Primary lane | First-wave assignment |
| --- | --- | --- | --- |
| Luna 1 | `gpt-5.6-luna` | SDK, connectors, execution | C01/C02 clean-SHA rerun |
| Luna 2 | `gpt-5.6-luna` | product UX and client preflight | C03 ChatGPT/Gemini capability preflight only |
| Terra 1 | `gpt-5.6-terra` | backend/data/acceptance | freeze independent C01/C02 acceptance |
| Terra 2 | `gpt-5.6-terra` | architecture/integration | map MVP user-goal gaps to roadmap packages |
| Sol 1 | `gpt-5.6-sol` | security and evidence audit | read-only audit-runner/provenance review |
| Sol 2 | `gpt-5.6-sol` | integration and release audit | board/dependency/automation safety review |

## First execution wave

### W01 — C01/C02 clean-SHA audit rerun

- Status: `ACTIVE / W01R1 CONTROLLED REMEDIATION`
- Owner: Luna 1
- Depends on: H07
- Exclusive write ownership: `scripts/verify_checksums.py`, regenerated C01,
  C02 and containment evidence, their handoffs, and only the C01/C02 checklist
  lines after acceptance passes.
- Acceptance: stdlib-only verifier works from a clean checkout; immutable audit
  image is built from the exact committed source SHA; C01 is 14/14; C02 is
  15/15; containment is 0/0/0; no secrets appear; reports distinguish audit
  SHA, server SHA, server digest/revision and audit image digest.
- Delivery: local clean commit and reconciliable handoff. No C03 work.
- Current delivery: verifier fix `87e7b0a5...`; blocked handoff
  `1ebfaab004...`; hosted acceptance not run. Requires P0 remediation, a
  controlled integration SHA, and explicit authorization to publish the audit
  image to the existing staging Artifact Registry.
- Active executor: `01a04e8a-7759-71d0-8b58-7197260aec67`, based on canonical
  coordination SHA `1742751a...`; authorized staging scope is limited to the
  existing project/region/registry and a cumulative US$10 ceiling.

### W02 — Freeze C01/C02 acceptance

- Status: `DELIVERED / INTEGRATION PENDING`
- Owner: Terra 1
- Depends on: H07
- Exclusive write ownership:
  `docs/handoffs/roadmap/C01-C02-ACCEPTANCE-FREEZE-20260829.md` only.
- Acceptance: exact positive and negative probes, provenance fields, checksum
  algorithm, containment invariants, redaction rules and fail-closed criteria
  are specified before W01 is accepted.
- Delivery: local clean commit/handoff; no runtime or report edits.
- Delivery SHA: `79014e79fa2ca2af658d54cf5363d44ff29b0285`.

### W03 — C03 capability and checkpoint preflight

- Status: `DELIVERED / INTEGRATION PENDING`
- Owner: Luna 2
- Depends on: none for read-only preflight; implementation remains blocked by
  C02 and CP-4.
- Exclusive write ownership:
  `docs/handoffs/roadmap/C03-CAPABILITY-PREFLIGHT-20260829.md` only.
- Acceptance: current official capability matrix for ChatGPT and Gemini MCP
  connectivity/import/export; exact owner actions, account prerequisites,
  OAuth/redirect/scopes and unsupported steps; proposed primary/fallback
  surface. No credential, account or external mutation.
- Delivery SHA: `4977556c1402dae8a48d97ef41a90b83f8514b03`;
  ChatGPT web is the proposed primary and Gemini CLI the supported fallback;
  CP-4 remains open.

### W04 — MVP user-goal gap map

- Status: `DELIVERED / INTEGRATION PENDING`
- Owner: Terra 2
- Depends on: current roadmap and handoff.
- Exclusive write ownership:
  `docs/handoffs/roadmap/MVP-USER-GOAL-GAP-MAP-20260829.md` only.
- Acceptance: map MCP connection, authentication/account UI and cross-assistant
  export to existing packages; identify missing tasks, critical path,
  checkpoints and measurable end-to-end tests without marking implementation
  complete.
- Delivery SHA: `9df8d95a6a459baf9ddcd503e4589eb1aa468041`;
  portable MCP export/import is a confirmed roadmap gap.

### W05 — Independent audit-runner review

- Status: `DONE / NO-GO FINDINGS`
- Owner: Sol 1
- Write ownership: none.
- Acceptance: report actionable findings against W01's runner, provenance,
  redaction, OAuth realism, cross-tenant isolation and checksum design. Do not
  modify W01-owned files or certify before current evidence exists.
- Result: two P0 findings (image/SHA provenance and fail-open job/containment)
  plus P1 findings for SDK monkeypatching, OAuth overclaim, redaction and RLS.

### W06 — Coordination-system safety review

- Status: `DONE / COORDINATION NO-GO`
- Owner: Sol 2
- Write ownership: none.
- Acceptance: identify races, duplicate-dispatch risks, missing stop conditions,
  dependency errors and unsafe automation behavior. Do not change product code.
- Result: recurring lane dispatch is paused; only central monitor remains.

## Dependency backlog

The canonical 43-item checklist remains in `docs/roadmap_implementation.md`.
The remaining dependency order is:

- M3 connectors: C01 -> C02 -> CP-4 -> C03 -> C04 -> C05L -> C05A.
- M4 Memory Atlas: C05A -> A01; then A02, A03 and A04; then A05T -> A05L -> A05A.
- M5 Trusted Recall: A05A -> T01 -> T02 -> T03 -> T04 -> T05L -> T05A.
- M6 private managed beta: T05A -> B01 and B02 -> B03 -> CP-6 -> B04L -> B04T.
- M7 community release: B04T -> O01 -> O02 and O03 -> O04.
- M8 public beta/GA: B04T + O04 -> CP-8 -> G01L -> G01T -> CP-5/CP-8 -> G02 -> G03L -> G03A.

No downstream implementation becomes `READY` until the manager reconciles all
declared predecessors and records any required human checkpoint.

## Manager heartbeat

Every 10 minutes:

1. inspect active task states and this board;
2. never prompt an executor that is still active;
3. reconcile a completed task against worktree, final SHA, clean tree, handoff
   and current acceptance evidence;
4. publish one idempotent failure event if the delivery contract is broken;
5. open exactly the next dependency-ready wave after reconciliation;
6. notify only on dispatch, failure, decision-needed or completion;
7. stop and remove the heartbeat when the MVP success evidence is met or a
   material owner decision is required.
