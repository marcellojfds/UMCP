# R02 — lanes M2/M3 locais válidas integradas

**Status:** `DONE — local integration only`
**Base SHA:** `ab0dbc3c68ba71463c06860fcb2c57d7adef3247`
**Final functional delivery SHA:** `7dbb63e48b505c046f5aef2747bbfdadb6c4c465`
**Reconciliation:** this documentation-only commit records the immutable
functional delivery SHA; the final candidate `HEAD` is reported at completion.

## Acceptance frozen before implementation

[`R02-ACCEPTANCE.md`](R02-ACCEPTANCE.md) was committed as
`b9b7fb05b53d760c9b31c7a4171e0231fdb66a79` before importing the lanes. It
requires local fail-closed hosted tests, preservation of M1 HTTP transport,
and synthetic v1 connector conformance and recipe on one candidate.

## Integrated paths and sources

- Hosted trust boundary from `81e6a33`; local gateway from `5d48fd3` and
  handoff correction `39c01a1`: `src/omp/server/hosted_auth.py`,
  `src/omp/server/hosted_gateway.py`, `src/omp/adapters/mcp/hosted.py`, their
  tests, and M02 handoffs.
- Connector contract from `7f77314` and handoff correction `e6071eb`:
  `docs/contracts/mcp/v1/`, `examples/connectors/`, the contract conformance
  test, and its M03 handoff.
- Synthetic recipe from `79c559d` and handoff correction `37b2fb3`:
  `examples/connectors/recipe.*`, recipe conformance test, and M03 recipe
  handoff.
- The incidental `docs/contracts/mcp/v0/README.md` navigation change from the
  source lane was removed. No other path outside the R02 allowlist changed.

## Current commands and results

| Gate | Result |
| --- | --- |
| `pytest -q tests/unit/test_hosted_auth.py tests/contract/test_hosted_http_boundary.py tests/contract/test_hosted_gateway.py` | PASS — 22 passed |
| `pytest -q tests/contract/test_m1_http_transport.py` | PASS — 3 passed (one third-party deprecation warning) |
| `pytest -q tests/conformance/test_m03_connector_contract.py tests/conformance/test_m03_connector_recipe.py` | PASS — 5 passed |
| `python -m examples.connectors.recipe` | PASS — deterministic synthetic JSON journey |
| frozen `ruff check` command | PASS |
| `git diff --check` | PASS |
| candidate path audit | PASS — only R02 paths after removal of the v0 incidental change |

## Skips, claims and boundaries

No Docker, GCP, IaC, workflow, deploy script, public listener, network,
provider, credential, real user/data/e-mail, holdout, push, PR, tag, release
or publication was run or changed.

Permitted claim: the local hosted seam fails closed with synthetic verifier
fixtures; it has only the internal `/_hosted_boundary/{tool_name}` test seam
and is explicitly non-publishable. The v1 connector contract and recipe pass
offline using synthetic `chatgpt-sim`, `claude-sim`, and `tenant-b-sim` labels.

Prohibited claims: M2 hosted completion, public `/mcp`, OAuth/OIDC, real IdP,
GCP/staging readiness, deployment, real-client support, M3 completion, beta,
release or production readiness.

## Rollback and next blockers

Rollback: locally revert the R02 acceptance, integration and reconciliation
commits; no remote state exists. The next blocked packages are H01 (reconcile
GCP decision/architecture), then H03/H04 for an authorized Streamable HTTP
runtime and identity/consent controls. M3 remains blocked on H07 and controlled
then real-client evidence; its synthetic contract and recipe are only
preflight evidence.
