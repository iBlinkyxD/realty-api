"""add realtor questionnaire fields to upgrade_requests

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-06-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'i0j1k2l3m4n5'
down_revision = 'h9i0j1k2l3m4'
branch_labels = None
depends_on = None


def upgrade():
    # IF NOT EXISTS so the chain can also run against a create_all-built schema
    op.execute("""
        ALTER TABLE upgrade_requests
            ADD COLUMN IF NOT EXISTS years_experience INTEGER,
            ADD COLUMN IF NOT EXISTS specialties      TEXT,
            ADD COLUMN IF NOT EXISTS bio              TEXT;
    """)


def downgrade():
    op.drop_column("upgrade_requests", "bio")
    op.drop_column("upgrade_requests", "specialties")
    op.drop_column("upgrade_requests", "years_experience")
