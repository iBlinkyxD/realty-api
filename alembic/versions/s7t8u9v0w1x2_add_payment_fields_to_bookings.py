"""add payment fields to bookings

Revision ID: s7t8u9v0w1x2
Revises: r6s7t8u9v0w1
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = 's7t8u9v0w1x2'
down_revision = 'r6s7t8u9v0w1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('bookings', sa.Column('paypal_order_id', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('paypal_authorization_id', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('paypal_capture_id', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('payment_status', sa.Text(), nullable=False, server_default='unpaid'))
    op.add_column('bookings', sa.Column('payout_status', sa.Text(), nullable=False, server_default='pending'))
    op.add_column('bookings', sa.Column('booked_price_per_day', sa.Numeric(10, 2), nullable=True))
    op.add_column('bookings', sa.Column('needs_admin_review', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('bookings', 'needs_admin_review')
    op.drop_column('bookings', 'booked_price_per_day')
    op.drop_column('bookings', 'payout_status')
    op.drop_column('bookings', 'payment_status')
    op.drop_column('bookings', 'paypal_capture_id')
    op.drop_column('bookings', 'paypal_authorization_id')
    op.drop_column('bookings', 'paypal_order_id')
