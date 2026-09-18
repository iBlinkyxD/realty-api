"""add assigned_realtor_id to users

Revision ID: 4f1c3506e1d4
Revises: 7c5858ba04a9
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = '4f1c3506e1d4'
down_revision = '7c5858ba04a9'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: production already has this column (applied outside Alembic). Raw SQL so the
    # foreign key is created together with the column and skipped with it when it already exists.
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_realtor_id UUID "
        "REFERENCES users(id) ON DELETE SET NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_assigned_realtor_id ON users (assigned_realtor_id)")


def downgrade():
    op.drop_index('ix_users_assigned_realtor_id', table_name='users', if_exists=True)
    op.drop_column('users', 'assigned_realtor_id', if_exists=True)
