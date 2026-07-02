"""add paypal_email to users

Revision ID: r6s7t8u9v0w1
Revises: q5r6s7t8u9v0
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'r6s7t8u9v0w1'
down_revision = 'q5r6s7t8u9v0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('paypal_email', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'paypal_email')
