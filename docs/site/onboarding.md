# Onboarding contract

## Community (available Alpha path)

1. Install the local PostgreSQL prerequisites and run the documented stdio
   setup in [`docs/installation.md`](../installation.md).
2. Treat `owner_id` as a trusted local partition only; it is not identity.
3. Connect a local MCP client using the stdio recipe.
4. Try a synthetic write, search, update, and forget. Exports are sensitive.

## Cloud (blocked pending Terra adapters)

The Cloud UI may expose these steps only once the server supplies the listed
capabilities:

1. Request a passwordless email sign-in link from a server-side endpoint. The
   response must be anti-enumeration and redirects must be allowlisted.
2. Exchange the verified callback for an HttpOnly, Secure session. The browser
   never accepts client-provided tenant or `owner_id`.
3. Display connections and their granted scopes. Consent and revocation are
   server operations authenticated from the session.
4. Require a preview and clear confirmation for forget, credential revocation,
   and account deletion. Use server-issued idempotency keys where the contract
   requires them.
5. Show export/deletion state and an audit-safe receipt, not sensitive payload
   or tokens.

The current web shell remains unavailable until this adapter is implemented.
