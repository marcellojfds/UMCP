# Experience lane progress

## M00 / G00 — baseline audit

- Outcome: branch-scoped Experience baseline audited and documented.
- Current SHA: `325faf32544e17c896ace07b8c712508c3ed7cce`.
- Demo: `cd apps/web && npm run check && npm test && npm run build`.
- Current gates: web check/unit/build pass; TypeScript SDK tests pass; browser
  E2E not run; root suite partial with environment and pre-existing contract
  failures recorded in `M00-EXPERIENCE-DONE.md`.
- Blocked external actions: Core integration handoff is absent; no backend
  changes are requested for G00.
- Next action: implement the isolated typed development Memory Inbox contract
  and UI, with explicit dev labeling and contract tests.

