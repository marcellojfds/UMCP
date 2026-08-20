# S06 — release governance and documentation

**Executed:** 2026-08-20
**Status:** documentation-ready, not publication-ready
**Publication:** no tag, GitHub Release, PyPI publication, commit, or push

## Decisions applied

The request supplied decision slots rather than final values. S06 applied the
conservative values recommended by the execution plan:

| Decision | Applied value | Boundary |
|---|---|---|
| License | Apache-2.0 | `LICENSE` and `pyproject.toml` |
| Package name | `open-memory-protocol` | confirmed existing package name |
| Version | `0.1.0a1` | package metadata and runtime version surfaces aligned |
| Public canonical language | English | new release-facing docs; historical technical baselines remain linked in Portuguese |
| Security reporting | GitHub Private Vulnerability Reporting | GitHub settings were not changed in this local session; no email was invented |
| Planned publication | GitHub Release only | PyPI is explicitly out of this plan |

The maintainer should confirm these values before publication. S06 did not
change remote repository settings.

## Evidence and claim discipline

Read for this session:

- `docs/EXECUTION_PLAN_QA_RELEASE.md`;
- `docs/privacy.md`;
- `docs/threat-model.md`;
- `docs/EVALS_PLAN.md`;
- `docs/protocol.md`;
- `docs/memory-model.md`;
- `README.md` and `pyproject.toml` before editing;
- `docs/handoffs/alpha/S02-ci-gate-b.md` and `docs/handoffs/alpha/S03-eval-dataset.md`;
- available Alpha Gate B and MCP/core handoffs for executable surface details.

There is no `S04` or `S05` handoff in `docs/handoffs` in this checkout. The
frozen `retrieval-v0` corpus is present, but the baseline report and its
quality/latency decision are not. Backup/restore/delete-retention and
privacy/operations evidence is also not available. The release docs therefore
do not claim retrieval quality, Gate B `GO`, backup readiness, or public Alpha
readiness.

The public docs explicitly preserve these constraints from privacy/threat
evidence:

- no E2EE, zero knowledge, hosted auth, hosted tenant isolation, or scale
  claim;
- `owner_id` is client-provided and trusted in local stdio composition, so it
  is logical scoping rather than authentication/authorization;
- content, provenance/evidence, relations, exports, backups, and embeddings
  are sensitive; embeddings are not anonymous;
- default exports omit embeddings, but exports remain sensitive and are not
  revoked by online forget;
- the PostgreSQL 16 + pgvector path is the supported release path and the
  file backend is demo-only.

## Files created or updated

Governance and release metadata:

- `LICENSE`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `CHANGELOG.md`
- `README.md`
- `pyproject.toml` — name retained, version changed to `0.1.0a1`, license changed to `Apache-2.0`
- `src/omp/__init__.py`, MCP capability/legacy metadata, and package workflow version assertion aligned to `0.1.0a1`

Release documentation:

- `docs/installation.md`
- `docs/mcp.md`
- `docs/sdk.md`
- `docs/cli.md`
- `docs/support-matrix.md`
- `docs/known-issues.md`
- `docs/roadmap.md`
- this handoff

## Verification

| Check | Result |
|---|---|
| Internal Markdown links in release docs | passed |
| `./scripts/gate-fast` | passed: Ruff, mypy, 44 unit/contract tests; 1 known Starlette/httpx deprecation warning |
| `./scripts/gate-postgres` with disposable Docker environment | passed: PostgreSQL 16.15, pgvector 0.8.6, migration head `0002_idempotency_operations`, 12 integration/E2E tests |
| Demo quickstart commands | passed in current environment and Python 3.11 venv with system dependencies |
| SDK example shape | passed with explicit demo transport and synthetic data |
| `omp --help` and CLI status smoke | passed |
| Package version import | passed: `omp.__version__ == 0.1.0a1` |
| Clean editable install from `pyproject.toml` | blocked: sandbox has no `hatchling` and network/DNS access was unavailable |
| Tags/remote publication | not performed; repository remains uncommitted/unpublished in this session |

The disposable PostgreSQL gate was run with elevated permission solely to
access the local Docker socket. Its container is removed by the gate cleanup.

## Remaining blockers before S07/publication decision

1. Add or recover the S04 handoff/report, including frozen-corpus metrics,
   slices, p50/p95, and the `hash/v1` decision.
2. Add or recover the S05 handoff, including backup/restore/delete-retention,
   outage/readiness, canary/secret scans, and accepted residual risks.
3. Enable and verify GitHub Private Vulnerability Reporting.
4. Produce constraints/lock and build/install wheel/sdist in a clean Python
   3.11 environment; the current sandbox could not install `hatchling`.
5. Run S07's independent clean-room audit and obtain maintainer approval
   before any tag, GitHub Release, or future PyPI decision.

No commit or push was made, per instruction.
