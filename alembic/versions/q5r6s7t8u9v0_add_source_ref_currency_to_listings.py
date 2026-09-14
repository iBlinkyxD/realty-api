"""add source_ref, currency, co_listing_agent_email to listings

Revision ID: q5r6s7t8u9v0
Revises: p4q5r6s7t8u9
Create Date: 2026-09-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'q5r6s7t8u9v0'
down_revision = 'p4q5r6s7t8u9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE listings
            ADD COLUMN IF NOT EXISTS source_ref TEXT,
            ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'USD',
            ADD COLUMN IF NOT EXISTS co_listing_agent_email TEXT;
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_listings_source_ref ON listings (source_ref) WHERE source_ref IS NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_listings_source_ref")
    op.drop_column('listings', 'co_listing_agent_email')
    op.drop_column('listings', 'currency')
    op.drop_column('listings', 'source_ref')
