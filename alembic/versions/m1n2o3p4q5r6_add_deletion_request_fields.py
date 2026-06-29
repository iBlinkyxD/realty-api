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
    op.add_column(
        'users',
        sa.Column('deletion_requested_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('users', 'deletion_requested_at')
