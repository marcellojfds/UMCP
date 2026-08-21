"""Add envelope storage columns for Cloud memory content and provenance.

The migration is additive: existing Community plaintext remains valid while
the Cloud repository starts writing ciphertext in a following code release.
Vectors remain outside this envelope so pgvector retrieval continues under
tenant RLS.
"""

from alembic import op

revision = "0006_cloud_envelope_storage"
down_revision = "0005_cloud_multitenancy_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("memories", "memory_versions"):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN content DROP NOT NULL")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN provenance DROP NOT NULL")
        op.execute(f"ALTER TABLE {table} ADD COLUMN content_ciphertext TEXT NULL")
        op.execute(f"ALTER TABLE {table} ADD COLUMN provenance_ciphertext TEXT NULL")
    op.execute("ALTER TABLE memories DROP CONSTRAINT ck_memories_content_nonempty")
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT ck_memories_content_or_ciphertext "
        "CHECK ((content IS NOT NULL AND length(trim(content)) > 0) "
        "OR content_ciphertext IS NOT NULL)"
    )
    op.execute(
        "ALTER TABLE memory_versions ADD CONSTRAINT ck_memory_versions_content_or_ciphertext "
        "CHECK ((content IS NOT NULL AND length(trim(content)) > 0) "
        "OR content_ciphertext IS NOT NULL)"
    )


def downgrade() -> None:
    # Safe only for disposable validation databases; Cloud ciphertext needs a
    # verified decrypt-and-backfill workflow before any production rollback.
    op.execute("ALTER TABLE memories DROP CONSTRAINT ck_memories_content_or_ciphertext")
    op.execute(
        "ALTER TABLE memory_versions DROP CONSTRAINT ck_memory_versions_content_or_ciphertext"
    )
    for table in ("memories", "memory_versions"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN provenance_ciphertext")
        op.execute(f"ALTER TABLE {table} DROP COLUMN content_ciphertext")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN content SET NOT NULL")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN provenance SET NOT NULL")
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT ck_memories_content_nonempty "
        "CHECK (length(trim(content)) > 0)"
    )
