"""add payment fields to bookings

Revision ID: b813c2be2e88
Revises: 0049637f62fa
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'b813c2be2e88'
down_revision = '0049637f62fa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: production already has these columns (applied outside Alembic).
    op.add_column('bookings', sa.Column('paypal_order_id', sa.Text(), nullable=True), if_not_exists=True)
    op.add_column('bookings', sa.Column('paypal_authorization_id', sa.Text(), nullable=True), if_not_exists=True)
    op.add_column('bookings', sa.Column('paypal_capture_id', sa.Text(), nullable=True), if_not_exists=True)
    op.add_column('bookings', sa.Column('payment_status', sa.Text(), nullable=False, server_default='unpaid'), if_not_exists=True)
    op.add_column('bookings', sa.Column('payout_status', sa.Text(), nullable=False, server_default='pending'), if_not_exists=True)
    op.add_column('bookings', sa.Column('booked_price_per_day', sa.Numeric(10, 2), nullable=True), if_not_exists=True)
    op.add_column('bookings', sa.Column('needs_admin_review', sa.Boolean(), nullable=False, server_default='false'), if_not_exists=True)


def downgrade() -> None:
    op.drop_column('bookings', 'needs_admin_review', if_exists=True)
    op.drop_column('bookings', 'booked_price_per_day', if_exists=True)
    op.drop_column('bookings', 'payout_status', if_exists=True)
    op.drop_column('bookings', 'payment_status', if_exists=True)
    op.drop_column('bookings', 'paypal_capture_id', if_exists=True)
    op.drop_column('bookings', 'paypal_authorization_id', if_exists=True)
    op.drop_column('bookings', 'paypal_order_id', if_exists=True)
