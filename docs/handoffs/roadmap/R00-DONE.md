# R00 — Canonical baseline handoff

**Status:** `DONE — local canonical baseline`  
**Branch:** `codex/roadmap-implementation`  
**Base SHA:** `faeadafef8589e2f3ef17de88f04114a3e02b742`
**Delivery evidence SHA:** `faeadafef8589e2f3ef17de88f04114a3e02b742` (no
product implementation was changed; the local commits after this evidence add
only the imported roadmap guide, this handoff, and the R00 checklist claim).

## Frozen acceptance contract

The delivery is accepted only when all of the following are evidenced from the
final local candidate:

1. the branch is based exactly on `faeadafef8589e2f3ef17de88f04114a3e02b742`;
2. the synthetic M1 ASGI transport acceptance passes with
   `pytest -q tests/contract/test_m1_http_transport.py`;
3. the current web gates pass with `npm test`, `npm run check`, and
   `npm run build` from `apps/web`;
4. the available unit, contract, conformance, and migration gates are run and
   classified accurately, without treating an unavailable dependency as pass;
5. no GCP or M2 implementation paths are incorporated;
6. divergence from `main` and `terra-alpha-recovery`, subsequent branch/commit
   inventory, and the PostgreSQL, socket, and browser classifications are
   documented; and
7. the final worktree is clean and only the R00 checklist line is checked.

## Scope and rollback

**In scope:** canonical local branch creation, synthetic evidence refresh,
baseline inventory, this handoff, and the copied roadmap guide.  
**Out of scope:** M2/GCP code or configuration, remote actions, real data,
holdout, services, credentials, deployment, release, or publication.  
**Rollback:** delete the local `codex/roadmap-implementation` branch after
switching away; no shared or remote state is changed.

## Inventory and divergence

- Canonical branch created locally from the exact M1 candidate above; `main`
  is `147` commits behind this candidate (`0` commits ahead), and
  `terra-alpha-recovery` is `142` commits behind (`0` ahead).
- The preserved M0/M1 path is `M00` integration/readiness through `d5b2513`,
  then M1 core `1569307`, local MCP `6d5b34b`, experience `e31709c`, and M1
  verification/readiness `3a33167` / `faeadaf`.
- Later local, non-incorporated work is inventoried by its refs: M2 contract
  `codex/m02-hosted-contract@ef949f3`, trust boundary
  `codex/m02-hosted-trust-boundary@81e6a33`, GCP gap/state
  `codex/m02-gcp-adoption-gap-report@106ec89` and
  `codex/m02-gcp-state@275fa1a`; M3 contract/plan
  `codex/m03-connector-contract@e6071eb` and
  `codex/m03-m08-product-plan@4639f7f`. None is merged or copied here.

## Current evidence

| Gate | Command | Freshness | Result |
| --- | --- | --- | --- |
| M1 synthetic ASGI acceptance | `pytest -q tests/contract/test_m1_http_transport.py` | current | PASS — 3 passed |
| Web test | `cd apps/web && npm test` | current | PASS — 8 passed |
| Web check | `cd apps/web && npm run check` | current | PASS |
| Web build | `cd apps/web && npm run build` | current | PASS — `dist/` built |
| Unit + contract repetition | `pytest -q tests/unit tests/contract` | current | 76 passed; 5 environment-blocked loopback cases (not a product pass) |
| M1 external HTTP contract/conformance | `pytest -q tests/contract/test_m1_http_contract.py tests/conformance/test_m1_portable_memory.py` | current | 4 environment-blocked failures before MCP initialization |
| PostgreSQL migrations | `./scripts/gate-postgres` | environment-blocked | Docker daemon socket access denied before disposable container startup |
| Aggregate fast gate | `./scripts/gate-fast` | current | FAIL — legacy mypy reports 23 errors in three existing M0/M1 files; this does not alter the explicit R00 ASGI/web gate and no code was changed |
| Browser E2E | capability preflight | not-run | managed browser/server lifecycle is unavailable for this execution |

The direct loopback-bind probe failed with `PermissionError: [Errno 1]
Operation not permitted`. Therefore HTTP socket tests are
`environment-blocked`, not evidence of a hosted or external-MCP pass. The
capability preflight also classified Docker as `environment-blocked`; it used
no external service, real data, credential, holdout, or user.

## Scope proof and claims

`git status --short` before committing contains only
`docs/roadmap_implementation.md` and `docs/handoffs/roadmap/R00-DONE.md`; the
only checklist mutation is the R00 checkbox in the copied roadmap guide. No
GCP/M2 implementation path is changed or introduced.

Permitted claim: M0+M1 are preserved on a new local candidate with current
synthetic ASGI and web evidence. Prohibited claims: hosted MCP, production,
release, PostgreSQL migration success, browser E2E, GCP readiness, or any
external integration.

## Rollback and next blocker

Rollback is limited to deleting the local `codex/roadmap-implementation`
branch after switching away; no shared or remote state changed.

R01 and R02 remain blocked on the roadmap manager's reconciliation of this
R00 handoff. Independent environmental follow-up is needed for the Docker
daemon, loopback socket and managed browser lifecycle; the pre-existing mypy
errors are a separate local quality finding and were not reclassified as pass.
