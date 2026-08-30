# T01 — hosted login route and authority boundary

**Status:** local implementation complete; staging promotion not-run.

**Base:** `4585b3432066a052453f6a85b3978e1d6cf6da66`.

## Acceptance frozen before implementation

`tests/contract/test_cloud_http.py::test_hosted_login_page_is_pkce_bound_and_rejects_client_authority`

The test requires `/login` to be served by the cloud HTTP application, expose
“Continue with Google”, require an OAuth authorization-code request with S256
PKCE before it can hand off to `/authorize`, and reject `owner_id` and
`tenant_id`.  It also checks no-store, no-referrer and anti-framing headers.

## Delivery and current evidence

- `/login` is now a server-owned OAuth handoff rather than a browser authority
  surface. It accepts only protocol fields already supplied by a client and
  delegates allowlist/PKCE validation to `OAuthServer.begin`.
- `owner_id` and `tenant_id` are rejected on both `/login` and hosted MCP tool
  calls. Neither field appears in the hosted tool schema.
- Current local commands passed on this package SHA:

  ```text
  python3.11 -m pytest tests/contract/test_cloud_http.py::test_hosted_login_page_is_pkce_bound_and_rejects_client_authority tests/contract/test_cloud_http.py::test_cloud_mcp_rejects_client_supplied_authority tests/contract/test_cloud_http.py::test_cloud_http_is_fail_closed_and_health_is_separate tests/unit/test_h07_oauth.py
  node --test apps/web/tests/*.test.mjs
  git diff --check
  ```

## Promotion and rollback

No image was built or promoted, and no staging OAuth state, Google identity,
token, connection or memory was created. Before promotion: build from this
clean commit, record the registry digest, and verify `/login` on that exact
digest. Rollback is traffic restoration to the former immutable digest
`sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`.

## Next package

T02 is a clean-SHA staging promotion and read-only provenance validation. It
must not call any client OAuth flow or claim cross-platform acceptance.
