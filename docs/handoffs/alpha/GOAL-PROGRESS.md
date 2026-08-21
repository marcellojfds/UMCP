# Luna Alpha goal progress

## Checkpoint S08-R2 / S09-preflight — 2026-08-20

- Base SHA before local changes: `4947ebfb3789558892c242e0d7a8743256f3656d`.
- Main worktree remains uncommitted; no stage, commit, push, tag, release or
  remote setting change was performed.
- S08 worktree remains preserved at
  `/private/tmp/umcp-s08-semantic-embedding-selection` on branch
  `s08-semantic-embedding-selection`, with its original untracked evidence.
- Frozen `retrieval-v0` corpus checksums remain unchanged from S04.
- Historical `UNBORN` hash reports and the earlier S08 report were preserved.
- Corrected S08 harness now applies both `query:` and `passage:` prefixes.
- Corrected S08 development report:
  `evals/reports/20260820T190703Z-4947ebfb3789-semantic-development/`.
- Corrected S08 result: MiniLM `precision@5=0.000`; E5
  `precision@5=0.755952`, intrusion `0.000`, abstention `1.000`,
  lifecycle/isolation `1.000`, p95 `15.932 ms`; decision `NO-GO`.
- Real PostgreSQL/gateway E5 development run also failed the same quality gate
  (`precision@5=0.755952`, p95 `32.223 ms`); `holdout_executed=false`.
- No holdout data was read or used for tuning.
- Experimental local E5 provider is offline-only and requires a pinned local
  revision; no network fallback is implemented.
- Migrations `0003_semantic_embedding_profile` and
  `0004_semantic_source_version` are additive: hash/v1 remains in vector(64),
  semantic rows use a parallel vector(384) table, and stale semantic vectors
  are excluded after a concurrent write or rollback.
- Disposable PostgreSQL 16.15 + pgvector 0.8.6 gate passed with 13 tests and
  zero skips, including coexistence, cutover and dual-profile forget cascade,
  at head `0004_semantic_source_version`.
- Local quality/unit/contract/eval gates passed; known warning is the existing
  Starlette/httpx deprecation warning.
- Added packaged `omp-migrate`, semantic optional dependency pins, a
  Python-3.11/macOS-arm64 constraints file, SBOM generation and fail-closed
  dependency-audit scripts.

## Checkpoint S08-R3-BGE / package-supply-chain — 2026-08-20

- User authorization received for exactly `BAAI/bge-small-en-v1.5` at revision
  `baab320e3049c6c62dd63560765566dd9083985e`, only for a new
  `semantic-development` experiment.
- Model snapshot is outside the repository at
  `/private/tmp/omp-bge-small-en-v1.5`; it uses `model.safetensors` only,
  size `133466304` bytes, SHA-256
  `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad`, MIT
  license, and an acquisition manifest with file hashes.
- The BGE harness uses normalized `[CLS]` pooling, the exact query-only
  instruction `Represent this sentence for searching relevant passages: `, no
  passage instruction, dimension `384`, threshold `0.78`, and unchanged
  `retrieval-v0` labels/gates. It did not read or execute holdout.
- BGE development report is preserved in
  `evals/reports/20260820T193539Z-4947ebfb3789-semantic-development/` and
  independently retained at
  `/private/tmp/omp-bge-eval-reports/20260820T193539Z-4947ebfb3789-semantic-development/`.
  Result: `NO-GO`, precision@5 `0.000`, intrusion `0.000`, abstention `1.000`,
  lifecycle/isolation `1.000`, p95 `20.788 ms`; all positive failures are
  recorded as identifiers only. BGE was not integrated into runtime or the
  PostgreSQL/gateway path because harness development did not pass.
- Final clean wheel/sdist build completed outside the checkout with
  `hatchling==1.32.0`, `build==1.5.0`; wheel SHA-256
  `3985b181714ca22a5aab06f77201f35e163dacff727f4908e7bf5aea49e9cfbd`, sdist
  SHA-256 `73aa1e41fe4798d37d7b182afc471e40fd064d6bd8a466c1652dc3efbc2571ac`.
  Both final artifacts exclude weights, datasets and reports.
- Isolated wheel install passed `pip check`; packaged `omp-migrate heads`
  returned `0004_semantic_source_version (head)`.
- `pip-audit --strict` passed for both runtime third-party dependencies and
  the build/audit toolchain with no known vulnerabilities after upgrading
  disposable-venv bootstrap tools to `pip==26.2.1` and `setuptools==84.0.0`.
- CycloneDX 1.5 SBOM was generated and validated with 47 components. Full
  versions, hashes, reports and commands are recorded in
  `/private/tmp/umcp-alpha-build-audit-manifest.json`.

## Current blockers / authorizations

- The authorized BGE experiment is a formal NO-GO under frozen gates; no
  semantic candidate is eligible for PostgreSQL/gateway integration.
- The GAMEPLAN Definition of Done still requires a sealed holdout, a clean
  committed SHA, remote required checks, branch-protection/PVR verification,
  and S07-R2 GO. The user explicitly prohibited holdout access and has not
  authorized stage/commit or remote GitHub changes, so those criteria remain
  pending and the goal must not be marked complete.

## External-state audit

- The BGE snapshot is isolated outside the repository and is not a package or
  commit payload.
- Disposable build/audit and wheel-install environments are under
  `/private/tmp`; the global Python environment was not modified.
- No remote Git write has been attempted; the origin exists but the worktree
  has no commit containing the current changes.
