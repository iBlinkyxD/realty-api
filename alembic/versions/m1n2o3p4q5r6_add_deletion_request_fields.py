"""add deletion_requested_at to users

Revision ID: m1n2o3p4q5r6
Revises: l3m4n5o6p7q8
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'm1n2o3p4q5r6'
down_revision = 'l3m4n5o6p7q8'
branch_labels = None
depends_on = None


def upgrade():
    # IF NOT EXISTS so the chain can also run against a create_all-built schema
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS deletion_requested_at TIMESTAMPTZ;
    """)


def downgrade():
    op.drop_column('users', 'deletion_requested_at')
