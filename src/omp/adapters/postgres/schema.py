"""SQLAlchemy Core schema for the PostgreSQL/pgvector adapter."""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

memories = Table(
    "memories",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("owner_id", String(256), nullable=False),
    Column("tenant_id", UUID(as_uuid=True), nullable=True),
    Column("space", String(256), nullable=True),
    Column("memory_type", String(64), nullable=False),
    # Community rows retain plaintext compatibility. Cloud rows use the
    # envelope columns below; vector data deliberately stays queryable under
    # tenant RLS rather than being encrypted at the application layer.
    Column("content", Text, nullable=True),
    Column("content_ciphertext", Text, nullable=True),
    Column("importance", Float, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("state", String(32), nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=True),
    Column("provenance", JSONB, nullable=True),
    Column("provenance_ciphertext", Text, nullable=True),
    Column("embedding_profile_id", String(128), nullable=False),
    Column("embedding_profile_version", String(128), nullable=False),
    Column("embedding_dimension", Integer, nullable=False),
    Column("embedding_metric", String(32), nullable=False),
    Column("idempotency_key", String(256), nullable=True),
    Column("idempotency_fingerprint", String(64), nullable=True),
    CheckConstraint("importance >= 0 AND importance <= 1", name="ck_memories_importance"),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_memories_confidence"),
    CheckConstraint("version >= 1", name="ck_memories_version_positive"),
    CheckConstraint(
        "(content IS NOT NULL AND length(trim(content)) > 0) OR content_ciphertext IS NOT NULL",
        name="ck_memories_content_or_ciphertext",
    ),
    CheckConstraint("length(trim(owner_id)) > 0", name="ck_memories_owner_nonempty"),
    UniqueConstraint("owner_id", "idempotency_key", name="uq_memories_owner_idempotency"),
    UniqueConstraint("owner_id", "id", name="uq_memories_owner_id"),
    UniqueConstraint("tenant_id", "id", name="uq_memories_tenant_id"),
    UniqueConstraint("tenant_id", "owner_id", "id", name="uq_memories_tenant_owner_id"),
)

memory_versions = Table(
    "memory_versions",
    metadata,
    Column(
        "memory_id",
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("version", Integer, nullable=False),
    Column("tenant_id", UUID(as_uuid=True), nullable=True),
    Column("memory_type", String(64), nullable=False),
    Column("content", Text, nullable=True),
    Column("content_ciphertext", Text, nullable=True),
    Column("importance", Float, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("state", String(32), nullable=False),
    Column("space", String(256), nullable=True),
    Column("occurred_at", DateTime(timezone=True), nullable=True),
    Column("provenance", JSONB, nullable=True),
    Column("provenance_ciphertext", Text, nullable=True),
    Column("changed_at", DateTime(timezone=True), nullable=False),
    Column("change_reason", String(256), nullable=False),
    CheckConstraint("version >= 1", name="ck_memory_versions_version_positive"),
    CheckConstraint(
        "(content IS NOT NULL AND length(trim(content)) > 0) OR content_ciphertext IS NOT NULL",
        name="ck_memory_versions_content_or_ciphertext",
    ),
    UniqueConstraint("memory_id", "version", name="uq_memory_versions_memory_version"),
    ForeignKeyConstraint(
        ["tenant_id", "memory_id"],
        ["memories.tenant_id", "memories.id"],
        ondelete="CASCADE",
        name="fk_memory_versions_tenant_memory",
    ),
)

memory_embeddings = Table(
    "memory_embeddings",
    metadata,
    Column(
        "memory_id",
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("profile_id", String(128), nullable=False),
    Column("tenant_id", UUID(as_uuid=True), nullable=True),
    Column("profile_version", String(128), nullable=False),
    Column("dimension", Integer, nullable=False),
    Column("metric", String(32), nullable=False),
    Column("vector", Vector(64), nullable=False),
    UniqueConstraint(
        "memory_id", "profile_id", "profile_version", name="uq_memory_embeddings_profile"
    ),
    ForeignKeyConstraint(
        ["tenant_id", "memory_id"],
        ["memories.tenant_id", "memories.id"],
        ondelete="CASCADE",
        name="fk_memory_embeddings_tenant_memory",
    ),
)

memory_embeddings_semantic = Table(
    "memory_embeddings_semantic",
    metadata,
    Column(
        "memory_id",
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("profile_id", String(128), nullable=False),
    Column("tenant_id", UUID(as_uuid=True), nullable=True),
    Column("profile_version", String(128), nullable=False),
    Column("source_version", Integer, nullable=False),
    Column("dimension", Integer, nullable=False),
    Column("metric", String(32), nullable=False),
    Column("vector", Vector(384), nullable=False),
    PrimaryKeyConstraint("memory_id", "profile_id", "profile_version"),
    CheckConstraint("dimension = 384", name="ck_semantic_embedding_dimension"),
    ForeignKeyConstraint(
        ["tenant_id", "memory_id"],
        ["memories.tenant_id", "memories.id"],
        ondelete="CASCADE",
        name="fk_memory_embeddings_semantic_tenant_memory",
    ),
)

memory_relations = Table(
    "memory_relations",
    metadata,
    Column("owner_id", String(256), nullable=False),
    Column("tenant_id", UUID(as_uuid=True), nullable=True),
    Column(
        "source_id",
        UUID(as_uuid=True),
        nullable=False,
    ),
    Column(
        "target_id",
        UUID(as_uuid=True),
        nullable=False,
    ),
    Column("relation_type", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["owner_id", "source_id"],
        ["memories.owner_id", "memories.id"],
        ondelete="CASCADE",
        name="fk_memory_relations_source_owner",
    ),
    ForeignKeyConstraint(
        ["owner_id", "target_id"],
        ["memories.owner_id", "memories.id"],
        ondelete="CASCADE",
        name="fk_memory_relations_target_owner",
    ),
    ForeignKeyConstraint(
        ["tenant_id", "owner_id", "source_id"],
        ["memories.tenant_id", "memories.owner_id", "memories.id"],
        ondelete="CASCADE",
        name="fk_memory_relations_tenant_source",
    ),
    ForeignKeyConstraint(
        ["tenant_id", "owner_id", "target_id"],
        ["memories.tenant_id", "memories.owner_id", "memories.id"],
        ondelete="CASCADE",
        name="fk_memory_relations_tenant_target",
    ),
    CheckConstraint("source_id <> target_id", name="ck_memory_relations_not_self"),
    UniqueConstraint(
        "owner_id", "source_id", "target_id", "relation_type", name="uq_memory_relations_edge"
    ),
)

idempotency_operations = Table(
    "idempotency_operations",
    metadata,
    Column("owner_id", String(256), nullable=False),
    Column("tenant_id", UUID(as_uuid=True), nullable=True),
    Column("operation_type", String(32), nullable=False),
    Column("idempotency_key", String(256), nullable=False),
    Column("fingerprint", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("memory_id", UUID(as_uuid=True), nullable=True),
    Column("result_version", Integer, nullable=True),
    Column("result_status", String(32), nullable=True),
    Column("claimed_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    PrimaryKeyConstraint(
        "owner_id", "operation_type", "idempotency_key", name="pk_idempotency_operations"
    ),
    CheckConstraint("operation_type IN ('update', 'forget')", name="ck_idempotency_operation_type"),
    CheckConstraint("status IN ('in_progress', 'completed')", name="ck_idempotency_status"),
    CheckConstraint("length(trim(idempotency_key)) > 0", name="ck_idempotency_key_nonempty"),
    CheckConstraint("length(fingerprint) = 64", name="ck_idempotency_fingerprint_sha256"),
)

# Cloud deletion evidence deliberately has no content, provenance or owner
# identifier.  It survives a logical restore so a worker can reapply the
# deletion before restored data becomes readable.
deletion_tombstones = Table(
    "deletion_tombstones",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False),
    Column("memory_id", UUID(as_uuid=True), nullable=True),
    Column("subject_id", UUID(as_uuid=True), nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=False),
    Column("reason", String(128), nullable=False),
)

# Audit metadata is intentionally structural only.  Content, provenance,
# owner IDs, tokens and ciphertext are never audit payloads.
audit_events = Table(
    "audit_events",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False),
    Column("principal_id", UUID(as_uuid=True), nullable=True),
    Column("action", String(128), nullable=False),
    Column("receipt_id", UUID(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("metadata", JSONB, nullable=False),
)

Index("ix_memories_owner_state", memories.c.owner_id, memories.c.state)
Index("ix_memories_owner_space", memories.c.owner_id, memories.c.space)
Index("ix_memories_owner_type", memories.c.owner_id, memories.c.memory_type)
Index("ix_memory_versions_memory", memory_versions.c.memory_id, memory_versions.c.version)
Index("ix_memory_relations_owner_source", memory_relations.c.owner_id, memory_relations.c.source_id)
Index("ix_memory_relations_owner_target", memory_relations.c.owner_id, memory_relations.c.target_id)
Index(
    "ix_idempotency_operations_owner_type",
    idempotency_operations.c.owner_id,
    idempotency_operations.c.operation_type,
)
Index(
    "ix_memory_embeddings_semantic_vector_cosine",
    memory_embeddings_semantic.c.vector,
    postgresql_using="ivfflat",
    postgresql_ops={"vector": "vector_cosine_ops"},
    postgresql_with={"lists": 10},
)
