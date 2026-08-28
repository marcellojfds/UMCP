# H07 — OAuth staging rollout, 2026-08-28

**Decision:** `NO-GO — H07 and C02 remain unchecked.`

This record is limited to project `umcp-mcp-staging-20260825`, region
`us-central1`, service `umcp-cloud-staging`, and job
`umcp-migrate-staging`.  No production resource, real user, secret value,
token, database URL, or test identity is recorded here.

## Rollout evidence

| Rollout | Source SHA | Immutable image digest | Ready revision | Migration | Result |
| --- | --- | --- | --- | --- | --- |
| OAuth enablement | `d7f2ae3ab7c5a5f40d479c46e49e4cd82cb086f7` | `sha256:e1f20cb8d75f7c7c62775ec2b367741f1fa2dc1f074478b2f20351b70b73d54e` | `umcp-cloud-staging-00013-rlp` | `umcp-migrate-staging-tn787`, completed; Alembic `0010_oauth_server -> 0011_oauth_authorization_codes` | routes enabled, then form-handler defect found by probe |
| Form-handler correction | `3c62f2ebd55fb62710a82e89e6f108c4281ea2aa` | `sha256:42e6654a09d7bbc9a36d2f3e58a2c3e2be738582590d1e8491c7a0961bdd1923` | `umcp-cloud-staging-00014-j72` (100% traffic) | `umcp-migrate-staging-525zs`, completed against the same SHA/digest; schema was already at head `0011` | current staging evidence below |

The runtime service account was granted `roles/secretmanager.secretAccessor`
only on the existing staging OAuth secret.  Cloud Run references that secret by
name and version; its value was never read.  Other hosted OAuth configuration
is public configuration or a one-way SHA-256 allowlist for the approved test
identity.

## Defect corrected

The first rollout proved metadata and authorization discovery but returned
`422` before `/token` and `/revoke` handlers.  With postponed annotations,
`Request` imported inside `create_cloud_http_app` was resolved by FastAPI as a
query field rather than Starlette's request object.  Commit `3c62f2e` moves the
FastAPI imports to module scope and adds contract coverage that asserts an
empty `/token` form reaches the handler (`400`) and empty `/revoke` is idempotent
(`200`).

Local validation: `11 passed, 2 deselected`; the two deselected existing tests
need a loopback socket that this sandbox may not bind.  `git diff --check`
passed before the commit.

## Current probes, revision `00014-j72`

All probes used the official Cloud Run service URL, carried no bearer token,
and did not retain response bodies.

| Endpoint / action | Result |
| --- | --- |
| `GET /readyz` | `200` |
| `GET /.well-known/oauth-protected-resource/mcp` | `200` |
| `GET /.well-known/oauth-authorization-server` | `200` |
| `POST /token` with empty form | `400` (handler reached; invalid grant rejected) |
| `POST /revoke` with empty form | `200` (idempotent) |
| `POST /mcp` without credentials | `401` |
| authorization request with disposable S256 PKCE/state | `302` to Google authorization host; URL/query not recorded |

The deployed implementation has authorization code plus PKCE S256, state and
authorization-code TTL/use-once records, opaque digest-only access/refresh
tokens, rotation, and revocation.  The state pattern was informed only by the
local personal-assistant reference's generic hash/TTL/use-once design; no
secret or configuration was copied.

## Remaining H07 gates

The controlled in-app browser returns `ERR_BLOCKED_BY_CLIENT` for both Cloud
Run service hostnames before it can reach Google login.  Therefore this session
did not transmit an authorization code or token and did not run the required
authorized journey: Google login/callback, token exchange, MCP call, refresh,
revoke, and post-revocation denial.

Independent H07 gates also remain unexecuted on the current digest: cross-
tenant RLS, KMS failure/swap/rotation, backup/restore/tombstones, hosted
secret/log scan, load, and alert evidence.  Consequently there is no basis to
mark H07 or its C02 dependency complete, and this is not authorization for a
private beta invitation.

## Safe continuation

Use a browser that can reach the authorized staging Cloud Run domain, sign in
only as the approved test identity, and obtain the full journey without writing
the temporary authorization code or tokens to a handoff or log.  Re-run the
remaining H07 gates on revision `00014-j72` (or a later single documented
revision) before reconsidering either checkbox.
