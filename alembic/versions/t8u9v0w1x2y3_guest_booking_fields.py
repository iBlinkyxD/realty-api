"""add guest booking fields to bookings table

Revision ID: t8u9v0w1x2y3
Revises: s7t8u9v0w1x2
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 't8u9v0w1x2y3'
down_revision = 's7t8u9v0w1x2'
branch_labels = None
depends_on = None


def upgrade():
    # Make buyer_id nullable so guest bookings (no platform account) can have a Booking row
    op.alter_column('bookings', 'buyer_id', nullable=True)
    # Store guest contact info directly on the booking when buyer_id is null
    op.add_column('bookings', sa.Column('guest_name', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('guest_email', sa.Text(), nullable=True))
    # Link back to the Lead row so for-owner query can deduplicate
    op.add_column('bookings', sa.Column('lead_id', UUID(as_uuid=True), nullable=True))


def downgrade():
    op.drop_column('bookings', 'lead_id')
    op.drop_column('bookings', 'guest_email')
    op.drop_column('bookings', 'guest_name')
    op.alter_column('bookings', 'buyer_id', nullable=False)
