"""Add a parallel 384-dimensional semantic embedding store.

The legacy ``memory_embeddings`` table remains vector(64) for hash/v1
rollback.  Semantic vectors are additive and are never mixed in one query.
Downgrade refuses to discard semantic rows; operators must use a verified
restore or a forward fix for non-disposable data.
"""

from alembic import op
from sqlalchemy import text

revision = "0003_semantic_embedding_profile"
down_revision = "0002_idempotency_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE memory_embeddings_semantic (
            memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            profile_id VARCHAR(128) NOT NULL,
            profile_version VARCHAR(128) NOT NULL,
            dimension INTEGER NOT NULL CHECK (dimension = 384),
            metric VARCHAR(32) NOT NULL,
            vector vector(384) NOT NULL,
            CONSTRAINT pk_memory_embeddings_semantic
                PRIMARY KEY (memory_id, profile_id, profile_version)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_memory_embeddings_semantic_vector_cosine
        ON memory_embeddings_semantic
        USING ivfflat (vector vector_cosine_ops) WITH (lists = 10)
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    count = connection.scalar(text("SELECT count(*) FROM memory_embeddings_semantic"))
    if count:
        raise RuntimeError(
            "refusing to drop non-empty semantic embeddings; restore or forward-fix instead"
        )
    op.execute("DROP TABLE memory_embeddings_semantic")
