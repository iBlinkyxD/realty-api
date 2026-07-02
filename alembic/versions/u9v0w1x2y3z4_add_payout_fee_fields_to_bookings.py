"""add payout fee fields to bookings

Revision ID: u9v0w1x2y3z4
Revises: t8u9v0w1x2y3
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa

revision = 'u9v0w1x2y3z4'
down_revision = 't8u9v0w1x2y3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('bookings', sa.Column('platform_fee', sa.Numeric(12, 2), nullable=True))
    op.add_column('bookings', sa.Column('payout_amount', sa.Numeric(12, 2), nullable=True))


def downgrade():
    op.drop_column('bookings', 'payout_amount')
    op.drop_column('bookings', 'platform_fee')
