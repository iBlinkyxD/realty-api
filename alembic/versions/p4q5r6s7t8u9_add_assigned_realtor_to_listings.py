"""add assigned_realtor_id to listings

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s7t8
Create Date: 2026-09-10

"""
from alembic import op
import sqlalchemy as sa

revision = 'p4q5r6s7t8u9'
down_revision = 'o3p4q5r6s7t8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE listings
            ADD COLUMN IF NOT EXISTS assigned_realtor_id UUID REFERENCES users(id) ON DELETE SET NULL;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_listings_assigned_realtor_id ON listings (assigned_realtor_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_listings_assigned_realtor_id")
    op.drop_column('listings', 'assigned_realtor_id')
