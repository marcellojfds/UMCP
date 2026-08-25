# R02 — acceptance contract (frozen)

**Status:** `frozen before implementation`
**Base SHA:** `ab0dbc3c68ba71463c06860fcb2c57d7adef3247`

## Outcome

Integrate only the valid local M2/M3 seams into the canonical candidate:
a hosted trust boundary and composed local gateway which fail closed, plus the
v1 connector contract and deterministic synthetic recipe. This is not a hosted
runtime, public MCP endpoint, OAuth/OIDC implementation, deployment, or M3
real-client claim.

## Acceptance commands

All commands must pass on one clean delivery SHA:

```text
pytest -q tests/unit/test_hosted_auth.py tests/contract/test_hosted_http_boundary.py tests/contract/test_hosted_gateway.py
pytest -q tests/contract/test_m1_http_transport.py
pytest -q tests/conformance/test_m03_connector_contract.py tests/conformance/test_m03_connector_recipe.py
python -m examples.connectors.recipe
ruff check src/omp/server/hosted_auth.py src/omp/server/hosted_gateway.py src/omp/adapters/mcp/hosted.py examples/connectors tests/unit/test_hosted_auth.py tests/contract/test_hosted_http_boundary.py tests/contract/test_hosted_gateway.py tests/conformance/test_m03_connector_contract.py tests/conformance/test_m03_connector_recipe.py
git diff --check
```

The hosted contract tests must demonstrate rejection before service dispatch for
missing, malformed, expired/revoked, wrong-issuer/audience, insufficient-scope,
and request-supplied tenant or owner authority. The M1 transport test remains
green. Connector conformance and recipe use only synthetic fixtures.

## Scope and rollback

Allowed paths are `src/omp/server/`, `src/omp/adapters/mcp/`,
`docs/contracts/mcp/v1/`, `examples/connectors/`, associated tests and roadmap
handoffs. Explicitly excluded: public runtime, GCP/IaC, Docker, workflows,
deploy scripts, providers, credentials, real users/data, release and publish.

Rollback is a local revert of the R02 delivery commits. No remote state may be
created or changed.
