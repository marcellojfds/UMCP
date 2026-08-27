# H03 repair — exact hosted MCP path

**Status:** local repair complete; not a hosted or OAuth claim.

## Problem and repair

The FastAPI parent disables slash redirects so that a reverse proxy cannot
downgrade an HTTPS MCP request.  Starlette's ordinary `Mount("/mcp", ...)`
then left the required exact public endpoint `POST /mcp` unmatched, returning
404 before the MCP authentication boundary.

`_ExactMCPRoute` now delegates only the exact `/mcp` ASGI scope to the
Streamable HTTP transport.  `/mcp/` remains deliberately unserved.  The
transport security configuration now derives HTTPS origins from the approved
host allowlist rather than accepting an arbitrary browser origin.

The first staging rollout also revealed that `ServerRuntime.startup()` made
the container exit when PostgreSQL was unavailable.  The hosted lifespan now
keeps the process live for that specific dependency failure: `/healthz` stays
available, `/readyz` truthfully returns `503`, and unauthenticated MCP remains
`401`.  This is not a database fallback and does not make the MCP service
ready.

## Current evidence

Executed on the delivery tree:

```text
python3.11 -m pytest -q tests/unit/test_cloud_entrypoint.py \
  tests/contract/test_cloud_http.py tests/contract/test_hosted_http_boundary.py \
  tests/unit/test_cloud_security.py tests/unit/test_h04_identity_contracts.py \
  -k 'not calls_tools_with_verified_tenant_principal and not conformance_runner_executes_against_local_mcp_gateway'
# 33 passed, 2 deselected

# after the readiness repair
# 34 passed, 2 deselected

python3.11 -m ruff check src/omp/server/official.py tests/contract/test_cloud_http.py
# passed
```

The two deselected contract tests open a loopback listener, which this managed
environment rejects with `PermissionError`.  They are environment-blocked, not
passes and not evidence for staging.

## Claims and next step

This repair proves the local exact-path routing and host/origin allowlist only.
It does not prove OAuth, an external MCP client, staging readiness, deployment,
or production.  The next material step is to build and deploy a reviewed image
to the authorized staging service, then re-run the black-box path probe before
attempting the still-missing OAuth flow.
