"""add password reset fields

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-06-29

"""
from alembic import op
import sqlalchemy as sa

revision = 'n2o3p4q5r6s7'
down_revision = 'm1n2o3p4q5r6'
branch_labels = None
depends_on = None


def upgrade():
    # IF NOT EXISTS so the chain can also run against a create_all-built schema
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS password_reset_token   TEXT,
            ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMPTZ;
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_password_reset_token
            ON users (password_reset_token);
    """)


def downgrade():
    op.drop_index('ix_users_password_reset_token', table_name='users')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'password_reset_expires')
