# M01-C — Memory Inbox Experience handoff

**Status:** `integration-ready`
**Lane:** M1-C Experience / Luna
**Commit:** `f214e08ef166bb443b9bb240709a789f1c795467`

The SHA above is the delivery/artifact commit described by this handoff. This
documentation-only remediation is a distinct follow-up commit; it corrects
the handoff record and does not replace the artifact SHA or alter the product.
**Contract:** `docs/handoffs/roadmap/M01-CORE-CONTRACT.md` (read in full before implementation)

This is a bounded lane delivery. It does not declare M1 ready, integrated, or
release GO. The experience is ready for Core/M1-B adapter integration.

## Delivered scope

- Added independent `#/inbox` Web experience under `apps/web`.
- Added JSDoc-typed UI contract fixtures for `MemorySnapshot`, provenance,
  `CaptureConsent`, recall items and connection snapshots.
- Added deterministic synthetic adapter covering candidate → confirmed →
  pinned/confirmed → stale → reviewed, plus candidate discard, terminal
  forget, tombstone-blocked restore/import and per-connection revoke.
- Added explicit consent and provenance presentation, including source client,
  source type, captured timestamp, space, consent mode/reason/policy and
  bounded `reason_retrieved`.
- Added loading, empty, error and success states with status announcements,
  labelled controls, keyboard-reachable native buttons/fields, responsive
  layout and reduced-motion-compatible existing styling.
- Added tests for frozen shapes, lifecycle/version transitions, scoped revoke,
  tombstone behavior, exact M1 tool mapping and Inbox render states.

No domain, application, migration, MCP, server, verification harness or
black-box acceptance paths were changed.

## Commands and results

| Command | Result |
| --- | --- |
| `cd apps/web && npm test` | PASS — 8 tests |
| `cd apps/web && npm run check` | PASS |
| `cd apps/web && npm run build` | PASS — `web build complete: dist/` |
| `git diff --check` | PASS |
| `pytest -q tests/verification/test_agent_board.py` | PASS — 2 tests |

The package has no separate lint script; `npm run check` is the available
syntax check. The built `apps/web/dist/` output is ignored and not part of the
lane changes.

## Screen/state evidence

Visual/DOM inspection was performed at the local static preview route
`http://127.0.0.1:4174/#/inbox` after the 4173 port was unavailable. Evidence
observed in the rendered page:

1. Candidate success state: `chatgpt-sim`, `conversation`, fixed UTC capture,
   `MBA`, `assisted`, `user_requested_memory`, version 1, and no recall result.
2. Confirmation state: candidate queue empty, same memory shown as
   `confirmed` version 2, with provenance/consent preserved.
3. Lifecycle state: `stale` version 3 exposes `Review → confirmed`; prior
   recall output is cleared after lifecycle mutation.
4. Recall state: explicit Work → MBA flow returns count 1 with
   `explicit_cross_space_semantic_match`, source `chatgpt-sim`, and space `MBA`.
5. Unit/fixture evidence covers empty, error/retry, discard/forget,
   already-absent replay, restore blocked by tombstone, scoped revoke and
   pinned/unpinned transitions. Destructive browser clicks were not executed
   during visual inspection.

The 4173 launch first returned sandbox `EPERM`; an approved temporary static
server on 4174 was used for the visual pass. This is an environment note, not
a product pass/fail claim.

## Integration contract pending

The UI accepts either:

- `window.__UMCP_M1_INBOX_ADAPTER__`, a server-owned adapter with the public
  result methods; or
- `window.__UMCP_M1_INBOX_INVOKE__`, which receives exact M1 tool names and
  arguments and calls the Streamable HTTP `/mcp` boundary.

The adapter maps only the frozen tools:
`memory.inbox.list`, `memory.inbox.confirm`, `memory.inbox.discard`,
`memory.pin`, `memory.recall`, `memory.update`, and `memory.forget`.

Core/M1-B still need to inject the real public result transport and enforce
trusted tenant/owner/connection scope, consent policy, expected-version
conflicts, revocation checks and tombstones server-side. Restore/import and
connection list/revoke are explicit injected seams because they are not new
M1 MCP tools in the frozen contract; the fixture deliberately returns
`restore_blocked_by_tombstone` without recreating content. The fixture is not
black-box acceptance evidence and must be replaced by the integrated adapter
before the M1 acceptance scenario is claimed.

## Boundary statement

`integration-ready`: the lane files, UI contract seam and focused evidence are
delivered. M1 remains pending Core/M1-B/Verification integration and no
release or milestone GO is implied.
