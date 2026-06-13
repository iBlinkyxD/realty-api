"""create pending_users table

Revision ID: e5f6a7b8c9d1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-13

Staging table for unverified registrations. Rows are promoted into the users
table on email verification and deleted from here. An hourly background task
also deletes rows where expires_at < now() to prevent unbounded growth from
abandoned signups.
"""
from alembic import op

revision = 'e5f6a7b8c9d1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS pending_users (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email                       TEXT NOT NULL,
            password_hash               TEXT NOT NULL,
            display_name                TEXT NOT NULL,
            phone                       TEXT,
            verification_code           TEXT,
            verification_code_expires_at TIMESTAMPTZ,
            verification_attempts       INTEGER NOT NULL DEFAULT 0,
            last_code_sent_at           TIMESTAMPTZ,
            expires_at                  TIMESTAMPTZ NOT NULL,
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_users_email ON pending_users (email);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pending_users_expires_at ON pending_users (expires_at);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pending_users;")
