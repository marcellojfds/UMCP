# ADR 0012 — Shared PostgreSQL with default-deny RLS

## Status

Accepted for productization design (2026-08-21).

## Decision

Cloud v1 uses shared PostgreSQL with `tenant_id` on all tenant data: users,
workspaces, memberships, identities, connections, credentials, consents,
memories, history, relations, embeddings, audit events, tombstones and usage.
RLS is enabled and forced on every tenant table. Policies default-deny and use
a transaction-local tenant setting populated only by a verified principal.

Application queries run through a restricted runtime role; migration and
break-glass roles are separate. Composite foreign keys, uniqueness constraints
and indexes include `tenant_id` where they express tenant-owned relations. A
missing, malformed, or mismatched context is an error, never an unscoped query.
Workers receive signed envelopes containing tenant, principal, job identity,
expiry and nonce, then establish the same transaction context.

## Consequences

The local owner-scoped schema is migrated additively and tested zero-to-head
and upgrade-in-place. Every repository method and worker job needs adversarial
cross-tenant tests. Database RLS is defense in depth, not a substitute for
gateway authorization.
