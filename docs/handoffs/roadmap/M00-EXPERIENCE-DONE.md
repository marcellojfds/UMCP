# M00 — Experience baseline / G00

Status: complete for the local Experience audit only. This is not an
integration or release approval.

## Scope

- Worktree: `/private/tmp/umcp-roadmap-experience`
- Branch: `roadmap/luna-experience`
- Delivered SHA: `325faf32544e17c896ace07b8c712508c3ed7cce`
- Roadmap input: G00 — audit Integration Recovery and incorporate the
  reliability playbook.
- Required handoff: `docs/handoffs/roadmap/PARALLEL-READY.md` was not present
  at this baseline and is therefore a recorded dependency gap, not inferred.

## Capability → acceptance test → demo

Capability: establish a reproducible, branch-scoped baseline for the web
Experience and SDK ownership before opening a new Experience capability.

Acceptance evidence:

- `apps/web`: unit tests pass (3/3), syntax check passes, build passes.
- `packages/sdk-typescript`: unit tests pass (2/2).
- Root pytest: 81 passed, 4 failed, 19 skipped. The failures are outside
  Experience ownership: two loopback binding tests are blocked by the
  environment (`PermissionError`) and two E5 config assertions expect a
  different whitespace normalization.

Demo command:

```sh
cd /private/tmp/umcp-roadmap-experience/apps/web
npm run check && npm test && npm run build
```

## Current gate freshness

| Gate | SHA | Freshness | Result | Artifact / note |
| --- | --- | --- | --- | --- |
| Web check | `325faf3` | current | pass | `apps/web/package.json` |
| Web unit/component | `325faf3` | current | pass (3/3) | `apps/web/tests/` |
| Web build | `325faf3` | current | pass | generated `apps/web/dist/` (ignored) |
| TypeScript SDK tests | `325faf3` | current | pass (2/2) | `packages/sdk-typescript/tests/` |
| Browser E2E | `325faf3` | not run | not verified | no browser runner is wired in baseline |
| Desktop/390px/keyboard/reduced motion | `325faf3` | not run | not verified | requires browser execution |
| Root pytest | `325faf3` | current | partial | 81 pass / 4 fail / 19 skip; see above |
| PostgreSQL/MCP E2E | `325faf3` | blocked by environment | not verified | no usable loopback/Docker test DB |
| Claim/link checks | `325faf3` | not run | not verified | no lane-local runner in baseline |

## Contracts, mocks, and pending endpoints

The Experience branch consumes the published v0 MCP contracts and the
server-owned Admin API boundary in `apps/web/src/admin-adapter.js`. No new
backend endpoint was changed in G00. Future Inbox work will use an isolated,
typed development adapter until Core publishes the capture/review contract;
the UI will show that state as development-only.

No production, hosted, release, or supported-client claim is made by this
handoff. No real data, email, paid service, holdout, push, PR, or deploy was
used.

## Next action

Open only the Memory Inbox milestone. Keep the WIP limit at one demonstrable
capability. Do not advance to Concepts or later Atlas surfaces until the Inbox
handoff and its current gates are complete, and do not present the development
adapter as a functional Core integration.

