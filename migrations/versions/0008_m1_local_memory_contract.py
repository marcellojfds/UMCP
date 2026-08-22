"""Add the additive M1 local memory lifecycle contract.

Existing v0 rows are projected to confirmed-compatible data and receive
explicit legacy provenance/consent markers.  The tombstone table intentionally
contains no content, provenance, query, vector or secret.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_m1_local_memory_contract"
down_revision = "0007_tenant_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("memories", "memory_versions"):
        op.add_column(table, sa.Column("capture_consent", JSONB(), nullable=True))
    memory_types = (
        "'fact', 'preference', 'decision', 'insight', 'hypothesis', 'lesson', 'goal', "
        "'project_context', 'concept', 'relationship', 'open_question', 'mental_note'"
    )
    memory_states = (
        "'active', 'candidate', 'confirmed', 'pinned', 'stale', 'superseded', "
        "'contradicted', 'archived'"
    )
    for table in ("memories", "memory_versions"):
        op.create_check_constraint(
            f"ck_{table}_memory_type_m1", table, f"memory_type IN ({memory_types})"
        )
        op.create_check_constraint(f"ck_{table}_state_m1", table, f"state IN ({memory_states})")

    op.execute("ALTER TABLE idempotency_operations DROP CONSTRAINT ck_idempotency_operation_type")
    op.create_check_constraint(
        "ck_idempotency_operation_type",
        "idempotency_operations",
        "operation_type IN ('update', 'forget', 'confirm', 'pin', 'discard')",
    )

    op.execute(
        """
        UPDATE memories
        SET state = 'confirmed'
        WHERE state = 'active'
        """
    )
    op.execute(
        """
        UPDATE memory_versions
        SET state = 'confirmed'
        WHERE state = 'active'
        """
    )
    op.execute(
        """
        UPDATE memories
        SET provenance = jsonb_set(
              COALESCE(provenance, '{}'::jsonb), '{source_client}', '"legacy-v0"'::jsonb, true
            )
        WHERE provenance IS NOT NULL
          AND NOT (provenance ? 'source_client')
        """
    )
    op.execute(
        """
        UPDATE memory_versions
        SET provenance = jsonb_set(
              COALESCE(provenance, '{}'::jsonb), '{source_client}', '"legacy-v0"'::jsonb, true
            )
        WHERE provenance IS NOT NULL
          AND NOT (provenance ? 'source_client')
        """
    )
    op.execute(
        """
        UPDATE memories
        SET capture_consent = jsonb_build_object(
          'mode', 'legacy_unverified', 'consent_id', 'legacy-v0-' || id::text,
          'reason_code', 'import_authorized', 'policy_version', 'v0-compat',
          'granted_at', created_at
        )
        WHERE capture_consent IS NULL
        """
    )
    op.execute(
        """
        UPDATE memory_versions
        SET capture_consent = jsonb_build_object(
          'mode', 'legacy_unverified', 'consent_id', 'legacy-v0-' || memory_id::text,
          'reason_code', 'import_authorized', 'policy_version', 'v0-compat',
          'granted_at', changed_at
        )
        WHERE capture_consent IS NULL
        """
    )

    op.add_column(
        "connections",
        sa.Column("capture_policy", sa.String(16), nullable=False, server_default="assisted"),
    )
    for name, type_ in (
        ("consent_id", sa.String(256)),
        ("mode", sa.String(32)),
        ("reason_code", sa.String(64)),
        ("policy_version", sa.String(128)),
    ):
        op.add_column("consents", sa.Column(name, type_, nullable=True))

    op.create_table(
        "memory_tombstones",
        sa.Column("owner_id", sa.String(256), nullable=False),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("memory_id", sa.UUID(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(128), nullable=False),
        sa.PrimaryKeyConstraint("owner_id", "memory_id", name="pk_memory_tombstones"),
        sa.CheckConstraint(
            "length(trim(owner_id)) > 0", name="ck_memory_tombstones_owner_nonempty"
        ),
    )
    op.create_index("ix_memory_tombstones_tenant", "memory_tombstones", ["tenant_id", "memory_id"])


def downgrade() -> None:
    # Disposable zero-to-head databases only.  M1 data must be restored or
    # forward-fixed before rollback; never silently discard tombstones.
    op.drop_index("ix_memory_tombstones_tenant", table_name="memory_tombstones")
    op.drop_table("memory_tombstones")
    for name in ("policy_version", "reason_code", "mode", "consent_id"):
        op.drop_column("consents", name)
    op.drop_column("connections", "capture_policy")
    op.drop_constraint("ck_idempotency_operation_type", "idempotency_operations", type_="check")
    op.create_check_constraint(
        "ck_idempotency_operation_type",
        "idempotency_operations",
        "operation_type IN ('update', 'forget')",
    )
    for table in ("memory_versions", "memories"):
        op.drop_constraint(f"ck_{table}_state_m1", table, type_="check")
        op.drop_constraint(f"ck_{table}_memory_type_m1", table, type_="check")
        op.drop_column(table, "capture_consent")
