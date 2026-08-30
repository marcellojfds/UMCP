# UMCP privacy boundary

**Updated:** 2026-08-30

UMCP has a local/self-hosted composition and a private hosted staging
composition. Neither is end-to-end encrypted or zero knowledge. The service
must decrypt memory content to retrieve it; authorized operators with access
to runtime, database, keys, exports, or backups may be able to read it.

## Identity and owner scope

In hosted staging, the OAuth client never supplies `owner_id` or `tenant_id`.
UMCP verifies its own access token, derives the principal and tenant, and maps
them to an internal owner scope. Google establishes identity during OAuth but
clients receive UMCP tokens, not authority to select another owner.

In local stdio, `owner_id` is caller-provided and trusted. That composition is
for a trusted local process only and must not be exposed directly to untrusted
users.

## Data inventory

| Data | Location | Sensitivity |
| --- | --- | --- |
| Memory content and versions | PostgreSQL | high |
| Provenance/evidence | PostgreSQL | high |
| Embeddings and searchable metadata | PostgreSQL/pgvector | high; embeddings are not anonymous |
| Relations, type, state, space, timestamps | PostgreSQL | medium/high |
| Tenant, subject, membership, credentials | PostgreSQL | high identity/security metadata |
| OAuth state, codes, access/refresh tokens | digests in PostgreSQL | high; raw values exist transiently at client/server boundaries |
| Portal session | Secure, HttpOnly cookie containing a short-lived UMCP access token | high |
| Exports and backups | operator/user-controlled storage | high |
| Application logs | Cloud/local logging | must be payload-free by design |

## Capture policy

Assistants should save only concise durable facts, preferences, decisions,
goals, and project context that the user explicitly asks to remember or that
is clearly useful long-term. Do not capture passwords, API keys, OAuth tokens,
financial credentials, private keys, medical records, or transient chat text.

The current MVP stores the chosen memory, not full conversation transcripts by
default.

## Retention and deletion

- Active memory persists until update/lifecycle change or `memory.forget`.
- Forget removes the tested online memory records transactionally in the
  application path.
- OAuth tokens expire and can be revoked; revocation does not delete memories.
- Portal logout revokes its current token and clears the portal cookie.
- Exports and backups are separate copies and are not automatically revoked by
  deleting the online record.
- A restore process must preserve/reapply deletion state before serving data.

## Current controls

- strict schemas and bounded inputs;
- server-derived hosted owner/tenant context;
- scoped UMCP tokens with expiry, refresh rotation, and revocation;
- PostgreSQL tenant context and RLS-oriented hosted schema;
- owner-scoped repository/application operations;
- KMS-backed hosted envelope-encryption path;
- payload-free application observability contract; and
- server-owned portal cookies and same-origin APIs.

These controls reduce risk but do not establish production audit, E2EE,
operator blindness, immediate backup deletion, or universal client safety.

## Staging policy

Private staging is allowlisted and should use synthetic or low-sensitivity
data. Do not invite external users or store sensitive personal data until the
beta privacy notice, deletion workflow, incident process, retention policy,
and release-SHA security review are complete.
