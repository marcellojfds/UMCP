# H07 staging re-audit — 2026-08-27

**Decision:** `NO-GO — H07 remains unchecked.`

## Scope and revision

Read-only audit of the authorized staging project
`umcp-mcp-staging-20260825`, service `umcp-cloud-staging`, region
`us-central1`.  Revision `umcp-cloud-staging-00006-wkf` receives 100% of
service traffic and exposes source provenance
`be50dedb46075d0606ee5b68467319097077efff` with image digest
`sha256:5dbb10482989bd5adca64e536658621d755a2e87be6b188e63ab9745d4bd6c67`.

No user data, token, OAuth authorization request, credential, database write,
or production action was used.

## Current observations

| Gate | Result | Evidence |
| --- | --- | --- |
| Exact hosted MCP endpoint | partial pass | unauthenticated `POST /mcp` is `401`, with provenance headers and no HTTP downgrade redirect |
| Runtime liveness/readiness separation | partial pass | process starts; `GET /readyz` returns `503 {"status":"not_ready"}` instead of failing the revision startup |
| OAuth protected-resource metadata | fail | `/.well-known/oauth-protected-resource/mcp` is application `404` |
| OAuth authorization-server metadata | fail | `/.well-known/oauth-authorization-server` is application `404` |
| Authorization endpoint | fail | `/oauth/authorize` is application `404` |
| Cloud SQL data plane | absent | no Cloud SQL instance exists in the project |
| Dedicated runtime identity | absent | only the default Compute service account exists |
| Secret state | partial | `umcp-google-oauth-client-secret` exists, but no runtime implementation consumes it |

`GET /healthz` is still answered as a frontend `404` without application
provenance or a corresponding revision log event.  It is not counted as a
liveness pass; `/readyz` and `/mcp` demonstrate that the new revision is
otherwise receiving traffic.

## Conclusion and next gate

H07 cannot promote M2 staging readiness.  The current deployment confirms the
exact fail-closed MCP boundary, but it lacks the OAuth metadata/authorization
composition, a usable private database, KMS/identity wiring, and the synthetic
authorized identities needed to execute the C02 lifecycle.  The next safe
roadmap package is the hosted data-plane and OAuth implementation/provisioning
under the existing staging-only budget and rollback boundary; C02 must not be
checked until that package produces a same-revision authenticated journey.
