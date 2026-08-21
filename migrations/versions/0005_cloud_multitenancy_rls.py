"""Add Cloud tenant control-plane and default-deny tenant RLS.

Community rows remain tenant-null and are intentionally invisible to the
restricted Cloud role. Production backfill is an explicit, audited forward job;
this revision never guesses a tenant from a client-provided owner id.
"""

# ruff: noqa: E501

from alembic import op

revision = "0005_cloud_multitenancy_rls"
down_revision = "0004_semantic_source_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE tenants (id UUID PRIMARY KEY, name VARCHAR(256) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    op.execute(
        "CREATE TABLE users (id UUID PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    op.execute(
        "CREATE TABLE memberships (id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, role VARCHAR(32) NOT NULL, UNIQUE (tenant_id, user_id))"
    )
    op.execute(
        "CREATE TABLE identities (id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, issuer VARCHAR(512) NOT NULL, subject VARCHAR(512) NOT NULL, UNIQUE (issuer, subject))"
    )
    op.execute(
        "CREATE TABLE connections (id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, client_id VARCHAR(256) NOT NULL, scopes TEXT[] NOT NULL, revoked_at TIMESTAMPTZ, UNIQUE (tenant_id, client_id))"
    )
    op.execute(
        "CREATE TABLE agent_credentials (id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, token_hash VARCHAR(256) NOT NULL UNIQUE, scopes TEXT[] NOT NULL, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    op.execute(
        "CREATE TABLE consents (id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, connection_id UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE, scopes TEXT[] NOT NULL, granted_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ)"
    )
    op.execute(
        "CREATE TABLE audit_events (id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, principal_id UUID, action VARCHAR(128) NOT NULL, receipt_id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), metadata JSONB NOT NULL DEFAULT '{}'::jsonb)"
    )
    op.execute(
        "CREATE TABLE deletion_tombstones (id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, memory_id UUID, subject_id UUID, deleted_at TIMESTAMPTZ NOT NULL DEFAULT now(), reason VARCHAR(128) NOT NULL)"
    )
    op.execute(
        "CREATE TABLE usage_counters (tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, period_start TIMESTAMPTZ NOT NULL, reads BIGINT NOT NULL DEFAULT 0, writes BIGINT NOT NULL DEFAULT 0, PRIMARY KEY (tenant_id, period_start))"
    )

    for table in (
        "memories",
        "memory_versions",
        "memory_embeddings",
        "memory_embeddings_semantic",
        "memory_relations",
        "idempotency_operations",
    ):
        op.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id UUID NULL REFERENCES tenants(id)")
        op.execute(f"CREATE INDEX ix_{table}_tenant_id ON {table} (tenant_id)")

    # Only a separately provisioned ``umcp_migrator`` role applies migrations.
    # PostgreSQL forbids CREATE ROLE inside Alembic's transaction, so role
    # creation belongs to deploy provisioning rather than this migration.
    tenant_tables = (
        "memberships",
        "identities",
        "connections",
        "agent_credentials",
        "consents",
        "audit_events",
        "deletion_tombstones",
        "usage_counters",
        "memories",
        "memory_versions",
        "memory_embeddings",
        "memory_embeddings_semantic",
        "memory_relations",
        "idempotency_operations",
    )
    community_tables = {
        "memories",
        "memory_versions",
        "memory_embeddings",
        "memory_embeddings_semantic",
        "memory_relations",
        "idempotency_operations",
    }
    for table in tenant_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        predicate = (
            "(tenant_id IS NULL AND current_setting('app.community_mode', true) = '1') OR "
            if table in community_tables
            else ""
        )
        op.execute(
            f"CREATE POLICY {table}_tenant_only ON {table} USING ({predicate}tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) WITH CHECK ({predicate}tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    # Limited to isolated zero→head test databases. Production Cloud data uses
    # a forward fix or verified restore as documented.
    tenant_tables = (
        "memberships",
        "identities",
        "connections",
        "agent_credentials",
        "consents",
        "audit_events",
        "deletion_tombstones",
        "usage_counters",
        "memories",
        "memory_versions",
        "memory_embeddings",
        "memory_embeddings_semantic",
        "memory_relations",
        "idempotency_operations",
    )
    for table in tenant_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_only ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for table in (
        "memories",
        "memory_versions",
        "memory_embeddings",
        "memory_embeddings_semantic",
        "memory_relations",
        "idempotency_operations",
    ):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_tenant_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN tenant_id")
    for table in (
        "usage_counters",
        "deletion_tombstones",
        "audit_events",
        "consents",
        "agent_credentials",
        "connections",
        "identities",
        "memberships",
        "users",
        "tenants",
    ):
        op.execute(f"DROP TABLE {table}")
