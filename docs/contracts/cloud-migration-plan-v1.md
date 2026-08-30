# Cloud multi-tenant migration and recovery plan v1

**Status:** staging schema path implemented; production migration and restore policy remain pending.

This document is the durable migration/recovery contract. The private staging
MVP has applied its required schema migrations, but that does not constitute a
production cutover or a verified production restore exercise. Current runtime
facts live in [`../CURRENT_STATE.md`](../CURRENT_STATE.md).

## Forward path

1. Create Cloud identity, tenant, membership, consent, credential, audit,
   tombstone and usage tables with no application cutover.
2. Add nullable `tenant_id` to every memory aggregate table; backfill only
   through an explicit maintainer-approved mapping job, then add composite
   constraints and `NOT NULL`.
3. Add encrypted replacement columns for content/provenance; dual-read only
   during a versioned migration, then verify ciphertext dumps before removing
   plaintext. No automatic plaintext fallback is permitted.
4. Enable and force default-deny RLS after all runtime paths set transaction
   context; separately test the migration role and restricted application role.
5. Create tenant-scoped tombstones before enabling async deletion/export jobs.

Each migration is additive and has zero-to-head, upgrade-from-existing and
PostgreSQL integration coverage. Data migrations are resumable, bounded and
audited. Production rollback is forward-fix or verified restore, not destructive
Alembic downgrade.

## Restore rule

Restore into isolation, validate revision/inventory, apply all durable
tombstones newer than the backup point, validate RLS/encryption/key access, and
only then allow traffic. A restore that cannot reapply deletions is unusable.

## Current implementation boundary

In the Cloud PostgreSQL implementation, a successful `memory.forget` writes
a tenant-scoped, content-free `deletion_tombstones` record in the same
transaction as the deletion. The record contains only the tenant, memory
reference, timestamp and `memory.forget` reason; it does not retain content,
provenance or the caller-owned identifier. The integration suite verifies this
alongside encrypted storage and key rewrap. Backup transport and a production
restore worker remain external-authorization work.

The same local Cloud repository emits tenant-scoped audit events for successful
write, update and forget mutations. They contain action, receipt, time and a
memory reference only—never memory content, provenance, owner IDs, secrets or
ciphertext.
