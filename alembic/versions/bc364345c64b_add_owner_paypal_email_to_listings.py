"""add owner_paypal_email to listings

Revision ID: bc364345c64b
Revises: 6c8499222d3a
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'bc364345c64b'
down_revision = '6c8499222d3a'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: production already has this column (applied outside Alembic).
    op.add_column('listings', sa.Column('owner_paypal_email', sa.Text(), nullable=True), if_not_exists=True)


def downgrade():
    op.drop_column('listings', 'owner_paypal_email', if_exists=True)
