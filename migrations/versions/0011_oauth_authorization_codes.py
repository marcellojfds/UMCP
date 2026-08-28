"""Add single-use OAuth authorization codes and token-family metadata."""

from alembic import op

revision = "0011_oauth_authorization_codes"
down_revision = "0010_oauth_server"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE oauth_states ADD COLUMN client_state text NOT NULL DEFAULT ''")
    op.execute(
        "CREATE TABLE oauth_authorization_codes (code_digest text PRIMARY KEY, "
        "state_digest text NOT NULL UNIQUE REFERENCES oauth_states(state_digest), "
        "client_id text NOT NULL, redirect_uri text NOT NULL, subject_id uuid NOT NULL, "
        "tenant_id uuid NOT NULL, membership_id uuid NOT NULL, credential_id uuid NOT NULL, "
        "scopes text[] NOT NULL, code_challenge text NOT NULL, expires_at timestamptz NOT NULL, "
        "used_at timestamptz)"
    )
    op.execute("ALTER TABLE oauth_tokens ADD COLUMN family_id uuid")
    op.execute("ALTER TABLE oauth_tokens ADD COLUMN issued_at timestamptz NOT NULL DEFAULT now()")
    op.execute("CREATE INDEX ix_oauth_tokens_active ON oauth_tokens (token_digest, expires_at) WHERE revoked_at IS NULL")
    op.execute("REVOKE ALL ON oauth_authorization_codes FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP INDEX ix_oauth_tokens_active")
    op.execute("ALTER TABLE oauth_tokens DROP COLUMN issued_at")
    op.execute("ALTER TABLE oauth_tokens DROP COLUMN family_id")
    op.execute("DROP TABLE oauth_authorization_codes")
    op.execute("ALTER TABLE oauth_states DROP COLUMN client_state")
