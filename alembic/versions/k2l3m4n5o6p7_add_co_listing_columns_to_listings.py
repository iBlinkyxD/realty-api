"""add co_listing columns to listings

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa

revision = 'k2l3m4n5o6p7'
down_revision = 'j1k2l3m4n5o6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS so the chain can also run against a create_all-built schema
    op.execute("""
        ALTER TABLE listings
            ADD COLUMN IF NOT EXISTS co_listing_enabled          BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS co_listing_brokerage        TEXT,
            ADD COLUMN IF NOT EXISTS co_listing_agent_name       TEXT,
            ADD COLUMN IF NOT EXISTS co_listing_agent_contact    TEXT,
            ADD COLUMN IF NOT EXISTS co_listing_commission_split NUMERIC(5, 2),
            ADD COLUMN IF NOT EXISTS co_listing_notes            TEXT,
            ADD COLUMN IF NOT EXISTS co_listing_status           TEXT;
    """)


def downgrade() -> None:
    op.drop_column('listings', 'co_listing_status')
    op.drop_column('listings', 'co_listing_notes')
    op.drop_column('listings', 'co_listing_commission_split')
    op.drop_column('listings', 'co_listing_agent_contact')
    op.drop_column('listings', 'co_listing_agent_name')
    op.drop_column('listings', 'co_listing_brokerage')
    op.drop_column('listings', 'co_listing_enabled')
