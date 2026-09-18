"""add guest booking fields to bookings table

Revision ID: f9901a9c3ae1
Revises: b813c2be2e88
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'f9901a9c3ae1'
down_revision = 'b813c2be2e88'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: production already has these columns (applied outside Alembic).
    # Make buyer_id nullable so guest bookings (no platform account) can have a Booking row
    op.alter_column('bookings', 'buyer_id', nullable=True)
    # Store guest contact info directly on the booking when buyer_id is null
    op.add_column('bookings', sa.Column('guest_name', sa.Text(), nullable=True), if_not_exists=True)
    op.add_column('bookings', sa.Column('guest_email', sa.Text(), nullable=True), if_not_exists=True)
    # Link back to the Lead row so for-owner query can deduplicate
    op.add_column('bookings', sa.Column('lead_id', UUID(as_uuid=True), nullable=True), if_not_exists=True)


def downgrade():
    op.drop_column('bookings', 'lead_id', if_exists=True)
    op.drop_column('bookings', 'guest_email', if_exists=True)
    op.drop_column('bookings', 'guest_name', if_exists=True)
    op.alter_column('bookings', 'buyer_id', nullable=False)
