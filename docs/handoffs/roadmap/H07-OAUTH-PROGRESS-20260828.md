# H07 OAuth progress — 2026-08-28

**Decision:** `NO-GO — H07 and C02 remain unchecked.`

## Staging rollout and migration evidence

Scope stayed within `umcp-mcp-staging-20260825`, `us-central1`,
`umcp-cloud-staging`, and `umcp-migrate-staging`.

| Field | Value |
| --- | --- |
| source SHA deployed | `365a73e7a2e3b409a4f1b8df6b5695840915cbfd` |
| immutable image | `southamerica-east1-docker.pkg.dev/umcp-mcp-staging-20260825/umcp-docker-repo/umcp@sha256:52ea05cf6bbab3f77e74d68ff548f1fc9b8b13bfd07ce574deca82eb7a527ddf` |
| Cloud Build | `2d9e9a11-ec01-4bc6-ac66-ce3f0303e11e` — success |
| ready revision | `umcp-cloud-staging-00011-gd6` |
| migration execution | `umcp-migrate-staging-6jxrh` — success |
| migration proof | Alembic upgraded `0009_h06_security_recovery` to `0010_oauth_server` |
| probe | `GET /readyz` = `200 {"status":"ready"}` with matching image-digest and source-SHA headers |

The migration job used the same digest and source-SHA label and ran
`python -m alembic upgrade head`. No secret value, token, database URL, or
identity was read into this record.

## Local OAuth implementation

Commit `f2f8f6753ce9bc26d68a9a3e1419f62fd516971a` adds the following local,
not-yet-deployed increment:

- protected-resource and authorization-server metadata; `/authorize`,
  `/oauth/callback`, `/token`, and `/revoke`;
- authorization-code flow with PKCE `S256` only;
- SHA-256 digests for state, codes, access tokens, and refresh tokens;
- 10-minute one-use state, two-minute one-use authorization code, opaque
  expiring access/refresh tokens, rotation, and revocation;
- migration `0011_oauth_authorization_codes`, including a separate code ledger,
  token-family metadata, and preservation of the client state for callback;
- fail-closed configuration: Google credentials must arrive through the
  `OMP_OAUTH_GOOGLE_CREDENTIALS` Secret Manager reference, and the service
  requires an explicit Google client ID, client/redirect allowlist, and SHA-256
  allowlist for the approved test email before OAuth routes are enabled.

The state design was informed by the neighboring personal-assistant project:
only random state, SHA-256 digest, TTL, and transactional one-time consumption
were reused. No configuration or secret was copied.

## Current blockers and next safe action

The existing staging secret `umcp-google-oauth-client-secret` is not a Google
credential JSON bundle (format check only; its value was never printed). No
public Google client ID, registered MCP client/redirect pair, or SHA-256 test
identity allowlist is available in the worktree or current Cloud Run config.
Consequently, the new runtime deliberately leaves OAuth unavailable instead of
accepting an unbounded identity or redirect.

Before deploying the OAuth increment and running the synthetic journey, supply
the authorized non-secret configuration values and confirm that the existing
Google client has `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/oauth/callback`
registered as its redirect URI. Keep the client secret only in Secret Manager.
Then deploy `f2f8f67` by digest, run migration `0011`, and execute discovery →
Google login/callback → token → MCP → refresh/revoke → denial after revocation
on that one revision. H07 remains unmarked until the full audit succeeds.

## Validation

- `python3 -m compileall -q src migrations`: pass.
- `git diff --check`: pass before commit.
- focused pytest: environment-blocked because the available Python 3.13 runtime
  has no `pytest` or project dependencies (`pydantic` absent).
