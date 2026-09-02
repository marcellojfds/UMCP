# Portal stabilization handoff — 2026-09-02

This is the restart point for the next UMCP portal session. It separates the
revision currently serving staging from later local work that has not been
pushed or deployed.

## Objective

Finish the first portal milestone by removing disruptive full-page transitions,
making the memory browser and Inbox coherent, hiding unsupported controls, and
keeping an authenticated owner session stable during normal navigation.

## Current position

| Item | Current value |
| --- | --- |
| Repository branch | `codex/account-vault-portal` |
| Local implementation HEAD before this handoff | `37661bf4e4b406be0f7f929cca24f245d0914fc8` |
| Remote branch HEAD | `820760f` |
| Working tree at handoff creation | clean before this handoff file |
| Staging project | `umcp-mcp-staging-20260825` |
| Cloud Run service | `umcp-cloud-staging` in `us-central1` |
| Active staging revision | `umcp-cloud-staging-portal-session`, 100% traffic |
| Deployed source | `820760f` |
| Deployed image | `sha256:88c95d5232f6a676d19a51a2db6de96eb7da168a626716c0850014835d528ab7` |
| Portal | `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/` |

Staging was rechecked through `gcloud run services describe` on 2026-09-02.
Production, IAM, secrets, database schema, and billing were not changed.

## What the supplied recording proved

The 19-second recording named `Screen Recording 2026-08-31 at 19.40.55.mov`
showed three symptoms occurring together:

1. navigating from the account shell could expose the public/marketing shell
   and its `LOADING SECURE DATA` state;
2. Inbox could show the old synthetic M01 candidate fixture instead of the
   owner's review queue;
3. unsupported Connections and Agents links remained visible, and Connections
   ended in a generic server error.

The shared cause was a stale, mixed-generation JavaScript module graph in an
already-open Safari tab. A second issue appeared during real-session validation:
the portal access token expires after ten minutes, while the callback previously
discarded the refresh token, so the first navigation after expiry returned 401.

## Deployed fixes

- `97318b5` — persistent account shell, in-app route rendering, working memory
  filters/search/card-list state, owner-memory Inbox, useful 401 state, and
  read-only feature gating.
- `17230aa` — `no-store, max-age=0` plus `Pragma: no-cache` for portal HTML and
  modules, and explicitly versioned CSS/config/application entrypoints.
- `820760f` — HttpOnly seven-day portal refresh cookie, automatic one-time
  refresh-and-retry after an access-token 401, refresh-token rotation, and
  revocation of both cookies/tokens on logout.

The refresh endpoint never returns bearer tokens to JavaScript. Access and
refresh values remain HttpOnly cookies; only opaque digests are persisted by the
OAuth token ledger.

## Validation completed

- Deployed canaries were created with zero traffic before promotion.
- Portal HTML, JavaScript, and CSS returned HTTP 200 with the required no-store
  headers and versioned entrypoints.
- Browser checks of isolated and canonical URLs reported no JavaScript errors.
- At deployed-source validation: web checks/build passed; 22/22 web tests passed;
  the portal HTTP contract, including refresh rotation, passed. Two unrelated
  loopback transport tests require socket access unavailable in the sandbox.
- At current local HEAD: `npm run check`, `npm test`, and `npm run build` pass;
  24/24 web tests pass.

## Important session caveat

A Safari login created before `820760f` has no refresh cookie. It will show
`SIGN IN REQUIRED` after its old ten-minute access token expires. The maintainer
must sign in once after the deployed fix; logins created after that point renew
silently for up to seven days. This one-time reauthentication was not performed
by Codex.

## Local work not yet deployed

Before this handoff commit, the local branch was nine implementation commits ahead of
`origin/codex/account-vault-portal`. These changes are not part of the active
staging image and must not be described as deployed:

1. `cb2238d` — portal navigation/responsive/docs polish;
2. `d97ecaf` — embedding LRU cache;
3. `a02b92d` — Connect AI guides and fixture-route transitions;
4. `aa76529` — parallel portal loading and token-verification caching;
5. `c1effe3` — autonomous-capture/WikiLink instructions;
6. `39d7d69` — preview auto-routing;
7. `55de610` — local server root/query handling;
8. `9a457e7` — interactive Knowledge Graph View;
9. `37661bf` — documentation for the graph/autonomous-capture experiment.

The combined local delta from the remote touches 18 files with roughly 558
insertions and 126 deletions. Review security and behavior changes in
`aa76529`, especially token-verification caching, before any push or deployment.

## Next actions

1. Sign in once at the canonical portal and exercise Today → Memories → filters
   and list view → Inbox in the same Safari tab. Confirm the account shell stays
   mounted and no public-shell flash or generic server error appears.
2. Leave the tab idle for more than ten minutes, then navigate again to prove
   the refresh-and-retry path against the real PostgreSQL OAuth ledger.
3. Review the nine local-only commits as one candidate stack. Run the relevant
   Python security/contracts plus web checks before deciding whether to push.
4. If that stack is accepted, deploy it by immutable digest to a zero-traffic
   revision, validate the tagged URL, and only then promote staging traffic.
5. Update `docs/CURRENT_STATE.md` only after the deployed SHA, digest, revision,
   and traffic have been reverified.

## Guardrails

- Staging is private and allowlisted; it is not production or a public beta.
- Do not change production, IAM, secrets, database schema, or billing as part of
  portal verification.
- Do not expose cookies, OAuth codes, bearer tokens, e-mail addresses, database
  connection strings, or Secret Manager values in logs or handoffs.
- Do not deploy the local nine-commit stack merely because web unit tests pass;
  it includes authentication-cache and product-scope changes.

## Prompt to resume

```text
Continue the UMCP portal work from
docs/handoffs/roadmap/PORTAL-SESSION-HANDOFF-20260902.md. First distinguish the
deployed staging source 820760f from local HEAD 37661bf, which is nine commits
ahead and not pushed. Verify the real Safari owner journey after one fresh login,
including navigation after more than ten minutes. Then review and test the local
commit stack, especially aa76529 token-verification caching, before proposing any
push or immutable canary deployment. Preserve the staging-only boundary and do
not change production, IAM, secrets, database schema, or billing.
```

## Relevant files

- `docs/CURRENT_STATE.md`
- `apps/web/src/app.js`
- `apps/web/src/admin-adapter.js`
- `apps/web/src/account-shell.js`
- `apps/web/src/memory-vault-view.js`
- `src/omp/server/official.py`
- `src/omp/server/oauth.py`
- `tests/contract/test_cloud_http.py`
- `apps/web/tests/admin-adapter.test.mjs`
