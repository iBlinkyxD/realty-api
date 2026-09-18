"""add paypal_email to users

Revision ID: 0049637f62fa
Revises: 4f1c3506e1d4
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = '0049637f62fa'
down_revision = '4f1c3506e1d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('paypal_email', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'paypal_email')
