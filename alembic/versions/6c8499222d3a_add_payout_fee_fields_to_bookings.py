"""add payout fee fields to bookings

Revision ID: 6c8499222d3a
Revises: f9901a9c3ae1
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa

revision = '6c8499222d3a'
down_revision = 'f9901a9c3ae1'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: production already has these columns (applied outside Alembic).
    op.add_column('bookings', sa.Column('platform_fee', sa.Numeric(12, 2), nullable=True), if_not_exists=True)
    op.add_column('bookings', sa.Column('payout_amount', sa.Numeric(12, 2), nullable=True), if_not_exists=True)


def downgrade():
    op.drop_column('bookings', 'payout_amount', if_exists=True)
    op.drop_column('bookings', 'platform_fee', if_exists=True)
