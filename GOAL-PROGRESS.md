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

### Final G00 evidence

- **Implementation SHA:** `7d798cbe3efb5eab16df5c9f7d931c1dfa9db537`.
- **Preflight:** `scripts/assert-worktree-context` now fails closed on path,
  branch, optional full/abbreviated SHA and dirty state; both valid and
  wrong-branch cases were exercised.
- **Acceptance:** `./scripts/demo-local-integration` passed; synthetic
  write→search→update→forget, cross-owner isolation, owner-boundary and
  fail-closed auth all passed.
- **Current gates:** `gate-fast` 73 passed; PostgreSQL 19 passed with
  PostgreSQL 16.15/pgvector 0.8.6, zero→head, downgrade/re-upgrade and head
  `0007_tenant_fks`; SDK 2 passed; web 3 passed plus check/build; CI safety,
  runtime-output on generated web output, and SBOM passed/generated.
- **Historical gates:** prior integration evidence in the post-mortem and
  `INTEGRATION-RC.md` remains historical unless independently rerun; the
  current run supersedes the local gate results listed above.
- **Not run:** browser desktop/390px visual, keyboard and reduced-motion E2E;
  holdout; hosted IdP/KMS/HSM/e-mail/queue/backup/deploy/release checks.
- **Environment-blocked:** dependency audit could not bootstrap pip because
  network access is unavailable. The initial sandboxed gate-fast attempt was
  loopback-blocked, then passed with the authorized local loopback capability.
- **Stagnation counters:** failures by same reason `1` (gate script cleanup,
  fixed); changes without green acceptance `0`; subsystem switches without
  demo `0`.
- **Next action:** wait for applicable `M00-EXPERIENCE-DONE.md` and
  `M00-VERIFICATION-DONE.md`, inspect them with `git show`, then integrate M00
  on `roadmap/integration`. Do not open the next milestone before that merge.
- **External blockers:** hosted and release work remains explicitly
  unauthorized; no independent release `GO` is issued.
