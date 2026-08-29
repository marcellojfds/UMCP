# UMCP roadmap progress

## Active milestone: W01R1 — C01/C02 controlled integration and remediation

### Milestone contract (frozen before remediation)

- **Outcome:** reconcile W01-W04 on one local line, repair the W05 fail-open
  findings, and accept C01 then C02 only from one immutable, redacted staging
  audit cycle tied to a clean source commit.
- **Acceptance command:** local audit-contract tests and
  `python3 -S scripts/verify_checksums.py` pass; after an immutable image is
  published by digest, `python3 scripts/run_c01_c02_audit.py` exits zero only
  for C01 14/14, C02 15/15, all required negatives, containment 0/0/0,
  matching provenance, checksums and redaction in one `audit_cycle_id`.
- **Demo:** the single audit wrapper builds no evidence itself; it validates
  immutable image metadata, runs C01 before C02, runs containment last, stages
  reports, scans all allowed sinks, and replaces canonical reports only after
  every gate passes.
- **Paths:** `Dockerfile.audit`, `src/omp/sdk/`,
  `scripts/run_c01_c02_audit.py`, `scripts/verify_checksums.py`, focused tests,
  C01/C02/containment reports and handoffs, checklist lines C01/C02,
  coordination board/state, and this progress file.
- **Dependencies:** local base `305568a3cc7be1987e0b85d4e8342a339521fb27`;
  integrated W01-W04; existing staging project
  `umcp-mcp-staging-20260825` in `us-central1`; server revision/digest/SHA from
  H07; cumulative external spend ceiling US$10.
- **Gates:** clean Git source; OCI revision label and baked source SHA equal
  `audit_source_sha`; immutable digest only; strict report schemas/totals;
  explicit negative results; exact integer containment 0/0/0; repr-safe
  credentials; sentinel scan of stdout/stderr/logs/artifacts; no unsupported
  OAuth-login or RLS claim; checksums; sequential C01 then C02 reconciliation.
- **Rollback:** delete only the temporary audit/containment Cloud Run jobs and
  retain the prior canonical reports/checklist unless every gate passes; the
  hosted server revision remains unchanged.
- **Out of scope:** production, service deployment, new services, external
  users, C03 execution, Git push/PR/tag/release, real data, holdout, secrets in
  evidence, and any spend beyond US$10.

### Current W01R1 local evidence

- **Integration line:** W02 acceptance freeze, W03 preflight, W04 gap map and
  W01 verifier/handoff were ancestry- and scope-checked, then cherry-picked
  linearly over `305568a3cc7be1987e0b85d4e8342a339521fb27`.
- **Focused tests:** 19 passed across audit contract, stdlib verifier,
  credential repr, explicit server error propagation, C01 runner and C02
  agent; `py_compile` and focused Ruff `F/I/UP` checks pass.
- **Fail-closed probes:** `omp.sdk.audit_entrypoint` without complete
  provenance exits 1; the wrapper rejects `unknown` and `:latest` before any
  cloud call; the current canonical reports are intentionally rejected because
  they predate `audit_cycle_id` and remain historical.
- **External state:** no image published and no Cloud Run job executed during
  remediation. Next safe boundary is a clean local source commit, followed by
  the single authorized image build/push and two necessary staging jobs.

### Prior milestone record: G00 — Integration Recovery

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
- **Paths:** `scripts/demo-local-integration`, `scripts/assert-worktree-context`, `GOAL-PROGRESS.md`,
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

- **Implementation SHA:** `1eb157fe07de99903c897f59b556bb24dcfc9acb`.
- **Preflight:** `scripts/assert-worktree-context` now fails closed on path,
  branch, optional full/abbreviated SHA and dirty state; both valid and
  wrong-branch cases were exercised.
- **Demo context:** a mismatched demo/worktree invocation is rejected before
  tests execute; valid Core and integration invocations both passed.
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
