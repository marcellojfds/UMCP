"""MVP 0 memory aggregate, history, relations and pgvector storage.

Revision ID: 0001_mvp0_initial
Revises:
"""

from alembic import op

revision = "0001_mvp0_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE memories (
            id UUID PRIMARY KEY,
            owner_id VARCHAR(256) NOT NULL,
            space VARCHAR(256),
            memory_type VARCHAR(64) NOT NULL,
            content TEXT NOT NULL,
            importance DOUBLE PRECISION NOT NULL CHECK (importance >= 0 AND importance <= 1),
            confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            state VARCHAR(32) NOT NULL,
            version INTEGER NOT NULL CHECK (version >= 1),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            occurred_at TIMESTAMPTZ,
            provenance JSONB NOT NULL,
            embedding_profile_id VARCHAR(128) NOT NULL,
            embedding_profile_version VARCHAR(128) NOT NULL,
            embedding_dimension INTEGER NOT NULL,
            embedding_metric VARCHAR(32) NOT NULL,
            idempotency_key VARCHAR(256),
            idempotency_fingerprint VARCHAR(64),
            CONSTRAINT ck_memories_content_nonempty CHECK (length(trim(content)) > 0),
            CONSTRAINT ck_memories_owner_nonempty CHECK (length(trim(owner_id)) > 0),
            CONSTRAINT uq_memories_owner_idempotency UNIQUE (owner_id, idempotency_key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory_versions (
            memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            version INTEGER NOT NULL CHECK (version >= 1),
            memory_type VARCHAR(64) NOT NULL,
            content TEXT NOT NULL CHECK (length(trim(content)) > 0),
            importance DOUBLE PRECISION NOT NULL CHECK (importance >= 0 AND importance <= 1),
            confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            state VARCHAR(32) NOT NULL,
            space VARCHAR(256),
            occurred_at TIMESTAMPTZ,
            provenance JSONB NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL,
            change_reason VARCHAR(256) NOT NULL,
            CONSTRAINT uq_memory_versions_memory_version UNIQUE (memory_id, version)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory_embeddings (
            memory_id UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
            profile_id VARCHAR(128) NOT NULL,
            profile_version VARCHAR(128) NOT NULL,
            dimension INTEGER NOT NULL,
            metric VARCHAR(32) NOT NULL,
            vector vector(64) NOT NULL,
            CONSTRAINT uq_memory_embeddings_profile UNIQUE (memory_id, profile_id, profile_version)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory_relations (
            owner_id VARCHAR(256) NOT NULL,
            source_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            target_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            relation_type VARCHAR(32) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT ck_memory_relations_not_self CHECK (source_id <> target_id),
            CONSTRAINT uq_memory_relations_edge UNIQUE (
                owner_id, source_id, target_id, relation_type
            )
        )
        """
    )
    op.execute("CREATE INDEX ix_memories_owner_state ON memories (owner_id, state)")
    op.execute("CREATE INDEX ix_memories_owner_space ON memories (owner_id, space)")
    op.execute("CREATE INDEX ix_memories_owner_type ON memories (owner_id, memory_type)")
    op.execute("CREATE INDEX ix_memory_versions_memory ON memory_versions (memory_id, version)")
    op.execute(
        "CREATE INDEX ix_memory_relations_owner_source ON memory_relations (owner_id, source_id)"
    )
    op.execute(
        "CREATE INDEX ix_memory_relations_owner_target ON memory_relations (owner_id, target_id)"
    )
    op.execute(
        "CREATE INDEX ix_memory_embeddings_vector_cosine ON memory_embeddings "
        "USING ivfflat (vector vector_cosine_ops) WITH (lists = 10)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_relations")
    op.execute("DROP TABLE IF EXISTS memory_embeddings")
    op.execute("DROP TABLE IF EXISTS memory_versions")
    op.execute("DROP TABLE IF EXISTS memories")
    # The extension is intentionally retained: another schema in the same
    # database may use pgvector. Removing it is an operator-level action.
