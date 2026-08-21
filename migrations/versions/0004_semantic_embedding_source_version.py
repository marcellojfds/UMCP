"""Tie parallel semantic vectors to the memory version they encode."""

import sqlalchemy as sa
from alembic import op

revision = "0004_semantic_source_version"
down_revision = "0003_semantic_embedding_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memory_embeddings_semantic",
        sa.Column("source_version", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE memory_embeddings_semantic AS embeddings
            SET source_version = memories.version
            FROM memories
            WHERE memories.id = embeddings.memory_id
            """
        )
    )
    op.alter_column("memory_embeddings_semantic", "source_version", nullable=False)
    op.create_check_constraint(
        "ck_semantic_embedding_source_version",
        "memory_embeddings_semantic",
        "source_version >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_semantic_embedding_source_version",
        "memory_embeddings_semantic",
        type_="check",
    )
    op.drop_column("memory_embeddings_semantic", "source_version")
