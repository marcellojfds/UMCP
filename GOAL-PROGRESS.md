# UMCP roadmap progress

## Active milestone: G00 — Integration Recovery

### Milestone contract (frozen before implementation)

- **Outcome:** produce a reproducible local integration candidate from the
  validated Terra/Luna integration HEAD, with current evidence separated from
  historical evidence and no production claim.
- **Acceptance command:** `./scripts/demo-local-integration` from this
  worktree exits zero and prints the validated SHA, branch/worktree context,
  synthetic journey result, and gate freshness summary.
- **Demo:** `./scripts/demo-local-integration` using only disposable synthetic
  data; it must exercise the existing local MCP write/search/update/forget
  path and fail closed for a forged owner/tenant context where the current
  local adapter exposes that check.
- **Paths:** `scripts/demo-local-integration`, `GOAL-PROGRESS.md`,
  `docs/handoffs/roadmap/M00-CORE-CONTRACT.md`,
  `docs/handoffs/roadmap/M00-CORE-DONE.md`.
- **Dependencies:** validated `product/integration` HEAD
  `5729c83e18cbd26c9ef759eaf7ff625a6060c6e1`; baseline commit `325faf3`;
  local Python dependencies; no external services.
- **Gates:** worktree context, Ruff/mypy/unit/contract, PostgreSQL,
  MCP stdio/HTTP, auth negative, cross-tenant, encryption/tombstone/worker,
  SDK/web/conformance, secret/PII scan and SBOM, each classified by freshness.
- **Rollback:** revert only G00-owned commits on `roadmap/luna-core`; preserve
  the baseline and Terra/Luna histories.
- **Out of scope:** M1 capture/spaces/tools, UI changes, hosted providers,
  real e-mail/data, holdout, deployment, push/PR/tag/release, and any release
  `GO` statement.

### Current evidence before implementation

| Gate | Classification | Evidence |
| --- | --- | --- |
| branch/worktree/SHA | current | `roadmap/luna-core` at `e1c3d99`, clean |
| Python fast gate | historical | post-mortem records earlier integration SHA |
| PostgreSQL zero→head | historical | `INTEGRATION-RC.md`, earlier integration SHA |
| MCP authenticated conformance | historical | `INTEGRATION-RC.md`, earlier integration SHA |
| SDK/web tests and build/check | historical | `INTEGRATION-RC.md`, earlier integration SHA |
| browser visual/keyboard E2E | not run | loopback/browser limitation in post-mortem |
| external IdP/KMS/queue/backup/deploy | environment-blocked / not run | outside local authorization |

### Heartbeat

- **Next action:** create the demo entrypoint, run it against synthetic local
  adapters, then run the current gates on this exact SHA.
- **Stagnation counters:** failures by same reason `0`; changes without green
  acceptance `0`; subsystem switches without demo `0`.
- **External blockers:** none for the local G00 work; hosted and release work
  remains explicitly unauthorized.
