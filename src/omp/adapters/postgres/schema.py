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
    Column("space", String(256), nullable=True),
    Column("memory_type", String(64), nullable=False),
    Column("content", Text, nullable=False),
    Column("importance", Float, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("state", String(32), nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=True),
    Column("provenance", JSONB, nullable=False),
    Column("embedding_profile_id", String(128), nullable=False),
    Column("embedding_profile_version", String(128), nullable=False),
    Column("embedding_dimension", Integer, nullable=False),
    Column("embedding_metric", String(32), nullable=False),
    Column("idempotency_key", String(256), nullable=True),
    Column("idempotency_fingerprint", String(64), nullable=True),
    CheckConstraint("importance >= 0 AND importance <= 1", name="ck_memories_importance"),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_memories_confidence"),
    CheckConstraint("version >= 1", name="ck_memories_version_positive"),
    CheckConstraint("length(trim(content)) > 0", name="ck_memories_content_nonempty"),
    CheckConstraint("length(trim(owner_id)) > 0", name="ck_memories_owner_nonempty"),
    UniqueConstraint("owner_id", "idempotency_key", name="uq_memories_owner_idempotency"),
    UniqueConstraint("owner_id", "id", name="uq_memories_owner_id"),
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
    Column("memory_type", String(64), nullable=False),
    Column("content", Text, nullable=False),
    Column("importance", Float, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("state", String(32), nullable=False),
    Column("space", String(256), nullable=True),
    Column("occurred_at", DateTime(timezone=True), nullable=True),
    Column("provenance", JSONB, nullable=False),
    Column("changed_at", DateTime(timezone=True), nullable=False),
    Column("change_reason", String(256), nullable=False),
    CheckConstraint("version >= 1", name="ck_memory_versions_version_positive"),
    CheckConstraint("length(trim(content)) > 0", name="ck_memory_versions_content_nonempty"),
    UniqueConstraint("memory_id", "version", name="uq_memory_versions_memory_version"),
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
    Column("profile_version", String(128), nullable=False),
    Column("dimension", Integer, nullable=False),
    Column("metric", String(32), nullable=False),
    Column("vector", Vector(64), nullable=False),
    UniqueConstraint(
        "memory_id", "profile_id", "profile_version", name="uq_memory_embeddings_profile"
    ),
)

memory_relations = Table(
    "memory_relations",
    metadata,
    Column("owner_id", String(256), nullable=False),
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
    CheckConstraint("source_id <> target_id", name="ck_memory_relations_not_self"),
    UniqueConstraint(
        "owner_id", "source_id", "target_id", "relation_type", name="uq_memory_relations_edge"
    ),
)

idempotency_operations = Table(
    "idempotency_operations",
    metadata,
    Column("owner_id", String(256), nullable=False),
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
