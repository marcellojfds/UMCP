"""H06 additive tenancy, RLS and recovery hardening.

This revision is deliberately provider-neutral.  It does not create hosted
roles or call a KMS/backup service; role provisioning and hosted recovery stay
behind CP-3 and the fail-closed local adapters.
"""

from alembic import op

revision = "0009_h06_security_recovery"
down_revision = "0008_m1_local_memory_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The M1 tombstone ledger was added after the first RLS migration.  It is
    # tenant-owned and must receive the same default-deny policy.
    op.execute("ALTER TABLE memory_tombstones ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_tombstones FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY memory_tombstones_tenant_only ON memory_tombstones "
        "USING ((tenant_id IS NULL AND current_setting('app.community_mode', true) = '1') "
        "OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK ((tenant_id IS NULL AND current_setting('app.community_mode', true) = '1') "
        "OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )

    # Composite indexes keep every tenant-scoped lookup and lifecycle ledger
    # on the same binding used by the composite foreign keys.
    indexes = (
        ("ix_memories_tenant_owner_state", "memories", "tenant_id, owner_id, state"),
        (
            "ix_memory_versions_tenant_memory_version",
            "memory_versions",
            "tenant_id, memory_id, version",
        ),
        ("ix_memory_embeddings_tenant_memory", "memory_embeddings", "tenant_id, memory_id"),
        (
            "ix_memory_embeddings_semantic_tenant_memory",
            "memory_embeddings_semantic",
            "tenant_id, memory_id",
        ),
        (
            "ix_memory_relations_tenant_owner_source",
            "memory_relations",
            "tenant_id, owner_id, source_id",
        ),
        (
            "ix_memory_relations_tenant_owner_target",
            "memory_relations",
            "tenant_id, owner_id, target_id",
        ),
        (
            "ix_idempotency_operations_tenant_owner_key",
            "idempotency_operations",
            "tenant_id, owner_id, operation_type, idempotency_key",
        ),
        (
            "ix_memory_tombstones_tenant_owner_memory",
            "memory_tombstones",
            "tenant_id, owner_id, memory_id",
        ),
        ("ix_audit_events_tenant_created", "audit_events", "tenant_id, created_at"),
        ("ix_deletion_tombstones_tenant_deleted", "deletion_tombstones", "tenant_id, deleted_at"),
    )
    for name, table, columns in indexes:
        op.execute(f"CREATE INDEX {name} ON {table} ({columns})")

    # Do not grant application roles from a migration.  If CP-3 has provisioned
    # the named roles, remove their accidental PUBLIC inheritance only; actual
    # least-privilege grants remain an explicit, reviewed provisioning step.
    op.execute(
        "REVOKE ALL ON "
        "memories, memory_versions, memory_embeddings, memory_embeddings_semantic, "
        "memory_relations, idempotency_operations, memory_tombstones, audit_events, "
        "deletion_tombstones, usage_counters FROM PUBLIC"
    )


def downgrade() -> None:
    # Safe only for a disposable zero-to-head validation database.  Hosted
    # rollback is forward-fix or verified isolated restore, never downgrade.
    op.execute(
        "GRANT ALL ON "
        "memories, memory_versions, memory_embeddings, memory_embeddings_semantic, "
        "memory_relations, idempotency_operations, memory_tombstones, audit_events, "
        "deletion_tombstones, usage_counters TO PUBLIC"
    )
    for name in (
        "ix_deletion_tombstones_tenant_deleted",
        "ix_audit_events_tenant_created",
        "ix_memory_tombstones_tenant_owner_memory",
        "ix_idempotency_operations_tenant_owner_key",
        "ix_memory_relations_tenant_owner_target",
        "ix_memory_relations_tenant_owner_source",
        "ix_memory_embeddings_semantic_tenant_memory",
        "ix_memory_embeddings_tenant_memory",
        "ix_memory_versions_tenant_memory_version",
        "ix_memories_tenant_owner_state",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.execute("DROP POLICY IF EXISTS memory_tombstones_tenant_only ON memory_tombstones")
    op.execute("ALTER TABLE memory_tombstones NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_tombstones DISABLE ROW LEVEL SECURITY")
