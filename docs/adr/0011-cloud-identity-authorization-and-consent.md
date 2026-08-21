# ADR 0011 — Cloud identity, authorization and consent

## Status

Accepted for productization design; identity-provider selection remains pending
the authorized two-provider spike (2026-08-21).

## Decision

Cloud accepts identity exclusively from a verified access token. A gateway
validates issuer, signature/JWKS, expiry, `nbf`, audience/resource binding,
revocation state, client binding and required scopes before constructing an
immutable `Principal`. Request-supplied `owner_id` is rejected in hosted
schemas and never reaches authorization or persistence selection.

OAuth 2.1/OIDC uses authorization code with PKCE for public clients, short
lived access tokens, refresh rotation, published authorization-server and
protected-resource metadata, registered redirect allowlists, per-integration
consent, and revocation. Minimum scopes are `memory:read`, `memory:write`,
`memory:delete`, `memory:export`, and `connections:manage`.

Agent PATs are one-time displayed opaque random credentials. Only a slow hash,
prefix/identifier, tenant, principal, scopes, expiry, revoke timestamp and
audit metadata are stored. Plain PATs, bearer tokens, cookies and emails are
prohibited from logs and telemetry.

## Consequences

The exact identity service/KMS integration is intentionally not selected until
authorized. No local credential or client-provided claim may impersonate a
Cloud user. Missing or unverifiable authorization fails closed with a safe
OAuth/MCP error.
