# H07 resumption handoff — 2026-08-27

**Decision at handoff:** `NO-GO — H07 and C02 remain unchecked.`

This records the current staging foundation and the precise remaining work for
the next session.  It supersedes no historical audit: the earlier H07 re-audit
correctly recorded the state that existed at that time.

## Repository and checklist

- working tree: `/private/tmp/umcp-pr1`;
- branch: `codex/fix-pr-1`;
- implementation head: `1908307e2e574e32e5ce3ea324793b0d828c6d12`;
- checked roadmap items: `R00`, `R01`, `R02`, `H01` through `H06` (`9/43`,
  20.9%);
- current dependency-ready item: `H07`.

The checkbox for H07 must remain open.  It needs a complete same-revision
authenticated lifecycle audit, not only a reachable MCP boundary or cloud
foundation.

## Staging foundation that is in place

Scope is limited to project `umcp-mcp-staging-20260825`, region
`us-central1`, and the `umcp-cloud-staging` service.  No production resource
or real end-user journey was used.

| Component | Current state |
| --- | --- |
| Cloud SQL | PostgreSQL 16 instance `umcp-postgres`, private IP only; database `umcp` and runtime user exist.  The database URL is held only in Secret Manager. |
| Network | VPC `umcp-private`, Private Service Access, and connector `umcp-run-private` are provisioned. |
| Runtime identity | `umcp-runtime@umcp-mcp-staging-20260825.iam.gserviceaccount.com` is attached to Cloud Run and has Cloud SQL client plus the least privilege needed for the referenced secrets and KMS key. |
| KMS | Key ring `umcp` and regional key `umcp-envelope` exist.  Hosted envelope encryption now calls Cloud KMS when `OMP_KMS_KEY_RESOURCE` is configured. |
| Migrations | Job `umcp-migrate-staging` executed successfully for the image deployed at the KMS stage. |
| Current service | `umcp-cloud-staging-00010-2bp` receives 100% traffic from image `sha256:72352a9b931d73824f3cfbf8339631621d269ecce95d675d484a1767646a3d49`, built from `d2eb47cc207bda20b96706e7776e904ee06d5365`. |

The current black-box observations are deliberately narrow:

- `GET /readyz` returned `200 {"status":"ready"}` with application
  provenance headers;
- unauthenticated `POST /mcp` returned `401` from the exact endpoint, without
  a downgrade redirect;
- `GET /healthz` still receives a frontend `404` without application
  provenance.  It is not a liveness pass and remains a platform-routing
  observation.

No secret values, OAuth tokens, database URLs, or client credentials are in
this handoff or source control.

## Code delivered but not yet rolled out

The branch adds two relevant capability increments after the currently
deployed source revision:

| Commit | Delivered capability | Rollout state |
| --- | --- | --- |
| `d2eb47c` | Cloud KMS-backed hosted envelope encryption and fail-closed behavior | deployed in revision `00010` |
| `1908307` | Alembic revision `0010_oauth_server` with persisted, digested OAuth state and opaque-token ledgers | local only; not built, deployed, or migrated in staging |

The migration creates `oauth_states` and `oauth_tokens` with expiration,
one-time-use/revocation fields and restrictive grants.  It is storage support,
not an OAuth server: no route currently consumes it.

## OAuth work still required

1. Build and promote the branch head, then execute `umcp-migrate-staging` for
   revision `0010_oauth_server`; verify migration state without printing
   secrets.
2. Implement the provider endpoints and metadata: protected-resource metadata,
   authorization-server metadata, authorize/callback, token, and revoke.
   Require PKCE S256, short-lived single-use authorization codes/states,
   opaque digested access and refresh tokens, expiry and revocation.
3. Wire the upstream Google identity configuration from Secret Manager; never
   add a client ID or secret to the repository or logs.  Validate the exact
   authorized redirect URI and use only the owner's approved test identity.
4. Connect the resulting verified principal safely to the hosted MCP path,
   including tenant/membership claims and fail-closed rejection for invalid,
   expired, or revoked credentials.
5. Run focused local tests and a synthetic staging journey on one deployed
   revision: discovery, authorization, callback, token exchange, MCP access,
   refresh/revoke, and post-revocation denial.  Then perform the remaining H07
   audit gates before changing any checkbox.

The nearby project `/Users/marcellojunqueirafranco/Documents/personal assistant`
is a design reference only.  Its calendar OAuth flow hashes a random state,
stores it with a ten-minute TTL, and consumes it once transactionally.  Reuse
that pattern, not its credentials or deployment configuration.

## Guardrails for the next session

- Preserve the dirty primary checkout; continue in `/private/tmp/umcp-pr1`.
- Keep the blast radius staging-only.  Do not use production, real end-user
  data, or unapproved identities.
- Treat the `9/43` checklist as authoritative.  Do not mark H07 or C02 until
  the clean evidence above exists.
- Keep immutable image digest, source SHA, revision, migration execution, and
  probe results in the next handoff.  Never record secret material.
