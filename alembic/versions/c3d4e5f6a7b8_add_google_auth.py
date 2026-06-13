"""add google auth

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-13

"""
from alembic import op

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id TEXT;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'users' AND indexname = 'ix_users_google_id'
            ) THEN
                CREATE UNIQUE INDEX ix_users_google_id ON users (google_id) WHERE google_id IS NOT NULL;
            END IF;
        END $$;
    """)
    op.execute("""
        ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_google_id;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_id;")
    op.execute("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;")
