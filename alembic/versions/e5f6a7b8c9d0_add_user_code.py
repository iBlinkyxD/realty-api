"""add user_code to users

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-13

Adds a sequential 7-digit-displayable integer user_code to the users table.
Existing rows are backfilled with row_number() ordered by created_at so that
the oldest account gets #1. The sequence is then reset to continue from the
highest assigned value, so new inserts pick up where the backfill left off.
"""
from alembic import op

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS users_user_code_seq START 1;
    """)
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS user_code INTEGER;
    """)
    # Backfill existing rows ordered by join date (oldest = 1)
    op.execute("""
        WITH ordered AS (
            SELECT id, row_number() OVER (ORDER BY created_at ASC) AS rn
            FROM users
        )
        UPDATE users
        SET user_code = ordered.rn
        FROM ordered
        WHERE users.id = ordered.id;
    """)
    # Advance sequence past the highest backfilled value so next INSERT continues from there
    op.execute("""
        SELECT setval(
            'users_user_code_seq',
            COALESCE((SELECT MAX(user_code) FROM users), 0) + 1,
            false
        );
    """)
    op.execute("""
        ALTER TABLE users
            ALTER COLUMN user_code SET DEFAULT nextval('users_user_code_seq');
    """)
    op.execute("""
        ALTER SEQUENCE users_user_code_seq OWNED BY users.user_code;
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_user_code ON users (user_code);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_user_code;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS user_code;")
    op.execute("DROP SEQUENCE IF EXISTS users_user_code_seq;")
