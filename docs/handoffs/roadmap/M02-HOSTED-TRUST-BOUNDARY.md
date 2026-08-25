# M02-T1 — Hosted trust boundary (local, synthetic)

## Status

Implemented and locally verified as a narrow, fail-closed composition seam.
This handoff is **not** M02 completion, a deployment, an OAuth/OIDC
integration, an IdP selection, RLS/KMS readiness, or a release approval.

## Delivered boundary

- `src/omp/server/hosted_auth.py` defines an injected `CredentialVerifier`
  port and turns only its verified claim result into an immutable `Principal`.
  The boundary validates issuer, audience, time window (`issued_at`, expiry,
  `not_before`), principal identifiers, auth method and required scope.
- `src/omp/adapters/mcp/hosted.py` is separate from the M01 local adapter.
  It authenticates before tool-argument validation and passes a
  `HostedToolCall(principal=..., arguments=...)` to the service.  Hosted
  request models forbid `owner_id`, `tenant_id`, and every other undeclared
  field; no caller authority selection reaches the service.
- `create_hosted_boundary_app()` exposes only
  `/_hosted_boundary/{tool_name}` for in-process adversarial tests. It is an
  internal test seam, deliberately not the public Streamable HTTP `/mcp`
  endpoint mandated by ADR 0010.

The verifier interface accepts no client claims separately from the bearer
credential and has no local token issuer, signing key, JWT parser, or
permanent credential. Test fixtures are synthetic verifier responses only.

## Acceptance evidence

| Command | Result |
| --- | --- |
| `pytest -q tests/unit/test_hosted_auth.py tests/contract/test_hosted_http_boundary.py` | PASS — 17 passed |
| `ruff check src/omp/server/hosted_auth.py src/omp/adapters/mcp/hosted.py tests/unit/test_hosted_auth.py tests/contract/test_hosted_http_boundary.py` | PASS |
| `pytest -q tests/unit/test_m1_core.py tests/unit/test_domain.py tests/unit/test_application.py tests/contract/test_m1_http_transport.py` | PASS — 26 passed (one third-party deprecation warning) |
| `pytest -q tests/unit/test_import_boundaries.py tests/unit/test_architecture.py` | PASS — 3 passed |
| `git diff --check` | PASS |

The hosted tests prove that missing, malformed, expired, wrong-issuer,
wrong-audience and insufficient-scope credentials never invoke the recording
service. They also prove rejection before dispatch for caller `owner_id` and
caller `tenant_id` (cross-tenant selection), and prove a valid synthetic
principal reaches the service without either field in its arguments.

## Current limitations and next authorization

- The verifier is a port only. A real implementation must be chosen and must
  verify signature/JWKS, revocation, client binding and consent in accordance
  with ADR 0011 before it can be composed into a hosted runtime.
- This change makes no GCP call and changes no local HTTP adapter, `http.py`,
  IaC, workflow, Dockerfile, deploy path, migration/RLS, KMS, or secrets.
- The internal route must not be published or represented as MCP/OAuth. A
  later, authorized integration must use the official Streamable HTTP runtime
  at `/mcp` and retain the same boundary tests plus real-provider adversarial
  coverage.
