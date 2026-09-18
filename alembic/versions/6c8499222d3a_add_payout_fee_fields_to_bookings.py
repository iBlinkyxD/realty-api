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
    op.add_column('bookings', sa.Column('platform_fee', sa.Numeric(12, 2), nullable=True))
    op.add_column('bookings', sa.Column('payout_amount', sa.Numeric(12, 2), nullable=True))


def downgrade():
    op.drop_column('bookings', 'payout_amount')
    op.drop_column('bookings', 'platform_fee')
