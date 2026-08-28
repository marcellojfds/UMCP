"""Persisted OAuth state, authorization codes and opaque tokens."""

from alembic import op

revision = "0010_oauth_server"
down_revision = "0009_h06_security_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE oauth_states (state_digest text PRIMARY KEY, client_id text NOT NULL, "
        "redirect_uri text NOT NULL, code_challenge text NOT NULL, scopes text[] NOT NULL, "
        "expires_at timestamptz NOT NULL, used_at timestamptz)"
    )
    op.execute(
        "CREATE TABLE oauth_tokens (token_digest text PRIMARY KEY, token_kind text NOT NULL, "
        "client_id text NOT NULL, subject_id uuid NOT NULL, tenant_id uuid NOT NULL, "
        "membership_id uuid NOT NULL, credential_id uuid NOT NULL, scopes text[] NOT NULL, "
        "expires_at timestamptz NOT NULL, revoked_at timestamptz)"
    )
    op.execute("REVOKE ALL ON oauth_states, oauth_tokens FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP TABLE oauth_tokens")
    op.execute("DROP TABLE oauth_states")
