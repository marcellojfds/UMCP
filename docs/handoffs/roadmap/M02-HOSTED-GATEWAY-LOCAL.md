# M02-T2 — Local hosted gateway composition

## Status

Implemented as a local, non-publishable ASGI composition seam. This handoff is
not M02 completion, a deployment, a hosted MCP endpoint, or an authorization
to operate cloud infrastructure.

This document was factually corrected in a new, documentation-only local
commit to record the immutable artifact SHA below; the gateway artifact itself
is unchanged.

## Delivered

- `src/omp/server/hosted_gateway.py` adds `create_local_hosted_gateway()`.
  It accepts an injected `CredentialVerifier`, a service, issuer/audience, and
  optional test clock/request-id factories, then composes the existing
  fail-closed `HostedAuthenticator` and hosted MCP boundary.
- The returned app exposes only the existing internal
  `/_hosted_boundary/{tool_name}` test seam. It has no `/mcp` route, OpenAPI,
  documentation endpoint, network listener, public hostname, or deployment
  configuration.
- `tests/contract/test_hosted_gateway.py` exercises the composition with only
  synthetic verified-claim fixtures. Missing, verifier-revoked, and expired
  credentials do not invoke the service. Caller-supplied `tenant_id` and `owner_id` are
  rejected, while the accepted command obtains tenant and principal values only
  from the verifier's `VerifiedCredential`.

## Acceptance evidence

| Command | Result |
| --- | --- |
| `pytest -q tests/contract/test_hosted_gateway.py tests/unit/test_hosted_auth.py tests/contract/test_hosted_http_boundary.py` | PASS |
| `ruff check src/omp/server/hosted_gateway.py tests/contract/test_hosted_gateway.py` | PASS |
| `git diff --check` | PASS |

## Commit and base

- Base: `codex/m02-hosted-trust-boundary@81e6a3392b63f95a4ef2fb9f6f8a2c0b511c1b6b`
- Gateway artifact commit: `5d48fd3cbb8b0e240df2b0495997bf3d663e5d7b`
- This factual SHA correction is recorded in a separate, documentation-only
  local commit.
- Ownership: `src/omp/server/hosted_gateway.py`,
  `tests/contract/test_hosted_gateway.py`, and this handoff only.

## Explicit limits

- No real IdP/OIDC integration, JWT signature verification, JWKS, revocation,
  client binding, or consent implementation.
- No deploy, public endpoint, GCP, IaC, Docker, workflow, RLS, KMS, secret, or
  migration change.
- No M02-complete assertion. A later authorized runtime integration must
  retain these adversarial boundary tests and use the official `/mcp`
  Streamable HTTP runtime from ADR 0010.
