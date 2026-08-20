"""Metadata-only idempotency ledger for update and forget operations.

Revision ID: 0002_idempotency_operations
Revises: 0001_mvp0_initial
"""

from alembic import op

revision = "0002_idempotency_operations"
down_revision = "0001_mvp0_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_memories_owner_id", "memories", ["owner_id", "id"])
    op.create_foreign_key(
        "fk_memory_relations_source_owner",
        "memory_relations",
        "memories",
        ["owner_id", "source_id"],
        ["owner_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_memory_relations_target_owner",
        "memory_relations",
        "memories",
        ["owner_id", "target_id"],
        ["owner_id", "id"],
        ondelete="CASCADE",
    )
    op.execute(
        """
        CREATE TABLE idempotency_operations (
            owner_id VARCHAR(256) NOT NULL,
            operation_type VARCHAR(32) NOT NULL,
            idempotency_key VARCHAR(256) NOT NULL,
            fingerprint VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            memory_id UUID,
            result_version INTEGER,
            result_status VARCHAR(32),
            claimed_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ,
            CONSTRAINT pk_idempotency_operations
                PRIMARY KEY (owner_id, operation_type, idempotency_key),
            CONSTRAINT ck_idempotency_operation_type
                CHECK (operation_type IN ('update', 'forget')),
            CONSTRAINT ck_idempotency_status
                CHECK (status IN ('in_progress', 'completed')),
            CONSTRAINT ck_idempotency_key_nonempty
                CHECK (length(trim(idempotency_key)) > 0),
            CONSTRAINT ck_idempotency_fingerprint_sha256
                CHECK (length(fingerprint) = 64)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_idempotency_operations_owner_type
        ON idempotency_operations (owner_id, operation_type)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS idempotency_operations")
    op.drop_constraint("fk_memory_relations_target_owner", "memory_relations", type_="foreignkey")
    op.drop_constraint("fk_memory_relations_source_owner", "memory_relations", type_="foreignkey")
    op.drop_constraint("uq_memories_owner_id", "memories", type_="unique")
