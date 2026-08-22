# M00 Local Readiness

## Decision

`READY` for the bounded local M00 readiness boundary.

**M00 local readiness READY; M01 ainda exige uma task/contrato novo e explícito.**

This is a local readiness decision only. It is not a release GO, production
approval, hosted-environment approval, or an opening of M01.

## Candidate and independent recommendation

- Final candidate SHA: `45fb2a4dc987773f6e9c61898e766ea18a6e1c9a`.
- Worktree: `/Users/marcellojunqueirafranco/.codex/worktrees/6490/UMCP`.
- Context: detached HEAD, accepted by the integration contract; branch value
  is empty.
- Preflight: `scripts/assert-worktree-context --expected-head
  45fb2a4dc987773f6e9c61898e766ea18a6e1c9a --expected-path "$PWD"
  --require-clean` passed.
- Tree: clean before the reruns; the final tree will be checked again after
  this handoff commit.
- Independent auditor: `docs/handoffs/roadmap/M00-READINESS-VERIFIED.md`
  recommends `READY`. Its audited SHA was `39de3377e8e235bb649a72a2bf9cbb4e58fc3154`;
  the final candidate is its documentation-only descendant containing that
  independent verification handoff.

## Required reruns on the final candidate

| Check | Result |
| --- | --- |
| `./scripts/demo-local-integration "$(git branch --show-current)" "$PWD"` | PASS; worktree context PASS; `4 passed, 8 deselected`; `2 passed, 3 deselected`; journey, cross-owner isolation, and fail-closed auth boundary PASS |
| `pytest -q tests/conformance tests/verification tests/evals/test_development_suites.py` | PASS; `16 passed` |
| `./scripts/check-gate-freshness docs/handoffs/roadmap/GATE-FRESHNESS.json --markdown` | PASS; exit 0; manifest machine-checkable at HEAD |
| `./scripts/assert-roadmap-integration-ready --milestone M00` | PASS; `sync=READY milestone=M00 ref=roadmap/integration` |
| `git diff --check` | PASS; exit 0 |

The demo used synthetic-only local data and printed `release-go=NOT-ISSUED`.
The focused suite emitted one known httpx/Starlette deprecation warning; it
did not affect the result.

## Freshness and limitations

`docs/handoffs/roadmap/GATE-FRESHNESS.json` was revalidated on the final
candidate. Its current passing evidence includes gate-fast, PostgreSQL/RLS,
MCP conformance, auth-negative, encryption/rotation, tombstone restore,
worker retry/restart, SDK, web, secret/PII, SBOM, and integration-readiness.
The manifest also preserves historical evidence and does not promote it to
current. In particular, the historical `root-pytest` result is `fail` and was
not used to infer M00 readiness.

The following are explicitly environment-blocked and are not passes:

- Browser E2E: `environment-blocked/blocked`; no connected browser backend was
  available, so no browser execution or pass is inferred.
- Dependency vulnerability audit: `environment-blocked/blocked`;
  `./scripts/audit-dependencies` could not bootstrap `pip-audit` because the
  restricted environment could not upgrade its temporary pip/wheel/setuptools
  environment. No dependency-audit pass is inferred.

These limitations bound this decision to the local candidate. They do not
support release, hosted-production, external IdP/KMS/HSM, real-email, durable
external-queue, holdout, or real-data claims.

## M00 proof and local transition

The integrated M00 proof is the Core-backed local journey: write, search,
update, and forget, with cross-owner isolation and fail-closed owner/auth
boundaries. The integrated handoff also records the local PostgreSQL/RLS,
encryption, worker, SDK, web, conformance, semantic, secret/PII, and runtime
output evidence. The independent reruns above confirm the consumable M00
journey and synchronization boundary on the final documentation-only
candidate.

This handoff closes only the local M00 readiness boundary. M01 remains closed;
advancing it requires a separate explicit task and a new M01 contract consumed
by the roadmap coordinator. No M01 work is opened by this document.
