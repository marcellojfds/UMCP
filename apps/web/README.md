# UMCP web portal

`apps/web` is the dependency-free browser shell served by the hosted UMCP
process under `/portal/`. In the current staging composition it is no longer
only a visual fixture: the server injects same-origin portal configuration,
establishes Google OAuth on `/portal/login`, and stores the UMCP access token
in a Secure, HttpOnly cookie.

## Current hosted routes

- `/portal/` — landing and browser application
- `/portal/login` — starts server-owned Google OAuth
- `/portal/callback` — validates state and establishes the portal session
- `/portal/api/session` — returns redacted subject/tenant session metadata
- `/portal/api/memories` — lists memories for the authenticated owner
- `/portal/api/memories/{id}` — returns one owner-scoped memory
- `/portal/api/logout` — revokes the portal token and clears the cookie

The browser never supplies a bearer token, owner ID, tenant ID, OAuth scope,
or arbitrary callback target. Authorization remains server-side.

## Local UI development

```bash
cd apps/web
npm test
npm run serve
```

Static/local use can still exercise deterministic adapters. Fixture state is
not hosted evidence. Production-facing claims require the same-origin portal
and a real authenticated journey.

## Current limitations

- memory list/detail only; edit, forget, search, export, and connection
  management remain roadmap work;
- the portal session is short-lived and has no automatic browser refresh;
- Google OAuth is allowlisted to the private staging identity; and
- the UI is not a production account-management surface.
