"""Bind Cloud memory children to the same tenant as their parent aggregate."""

from alembic import op

revision = "0007_tenant_fks"
down_revision = "0006_cloud_envelope_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable tenant IDs retain Community compatibility. PostgreSQL skips a
    # composite FK when its nullable tenant component is NULL; the original
    # memory_id/owner_id FKs remain in force for those rows.
    op.execute("ALTER TABLE memories ADD CONSTRAINT uq_memories_tenant_id UNIQUE (tenant_id, id)")
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT uq_memories_tenant_owner_id "
        "UNIQUE (tenant_id, owner_id, id)"
    )
    op.execute(
        "ALTER TABLE memory_versions ADD CONSTRAINT fk_memory_versions_tenant_memory "
        "FOREIGN KEY (tenant_id, memory_id) REFERENCES memories (tenant_id, id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE memory_embeddings ADD CONSTRAINT fk_memory_embeddings_tenant_memory "
        "FOREIGN KEY (tenant_id, memory_id) REFERENCES memories (tenant_id, id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE memory_embeddings_semantic "
        "ADD CONSTRAINT fk_memory_embeddings_semantic_tenant_memory "
        "FOREIGN KEY (tenant_id, memory_id) REFERENCES memories (tenant_id, id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE memory_relations ADD CONSTRAINT fk_memory_relations_tenant_source "
        "FOREIGN KEY (tenant_id, owner_id, source_id) "
        "REFERENCES memories (tenant_id, owner_id, id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE memory_relations ADD CONSTRAINT fk_memory_relations_tenant_target "
        "FOREIGN KEY (tenant_id, owner_id, target_id) "
        "REFERENCES memories (tenant_id, owner_id, id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    for table, constraint in (
        ("memory_relations", "fk_memory_relations_tenant_target"),
        ("memory_relations", "fk_memory_relations_tenant_source"),
        ("memory_embeddings_semantic", "fk_memory_embeddings_semantic_tenant_memory"),
        ("memory_embeddings", "fk_memory_embeddings_tenant_memory"),
        ("memory_versions", "fk_memory_versions_tenant_memory"),
        ("memories", "uq_memories_tenant_owner_id"),
        ("memories", "uq_memories_tenant_id"),
    ):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
