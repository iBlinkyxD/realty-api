"""add ghl columns to leads

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-06-23

"""
from alembic import op


revision = 'j1k2l3m4n5o6'
down_revision = 'i0j1k2l3m4n5'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE leads
            ADD COLUMN IF NOT EXISTS ghl_contact_id  TEXT,
            ADD COLUMN IF NOT EXISTS ghl_sync_error  TEXT,
            ADD COLUMN IF NOT EXISTS ghl_synced_at   TIMESTAMPTZ
    """)


def downgrade():
    op.execute("""
        ALTER TABLE leads
            DROP COLUMN IF EXISTS ghl_contact_id,
            DROP COLUMN IF EXISTS ghl_sync_error,
            DROP COLUMN IF EXISTS ghl_synced_at
    """)
