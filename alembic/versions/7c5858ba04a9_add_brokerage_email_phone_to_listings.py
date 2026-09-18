"""add brokerage email and phone to listings

Revision ID: 7c5858ba04a9
Revises: ed856ef1081c
Create Date: 2026-06-30 00:00:00.000000

co_listing_agent_contact is intentionally kept: the bulk importer populates it
and the dashboard displays it, so dropping it would discard imported data.
"""
from alembic import op
import sqlalchemy as sa

revision = '7c5858ba04a9'
down_revision = 'ed856ef1081c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('listings', sa.Column('co_listing_brokerage_email', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('co_listing_brokerage_phone', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('listings', 'co_listing_brokerage_phone')
    op.drop_column('listings', 'co_listing_brokerage_email')
