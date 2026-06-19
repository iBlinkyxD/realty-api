"""add lead status timestamps

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-06-18

"""
from alembic import op


revision = 'h9i0j1k2l3m4'
down_revision = 'g8h9i0j1k2l3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE leads
            ADD COLUMN IF NOT EXISTS assigned_at  TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS contacted_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS closed_at    TIMESTAMPTZ
    """)


def downgrade():
    op.execute("""
        ALTER TABLE leads
            DROP COLUMN IF EXISTS assigned_at,
            DROP COLUMN IF EXISTS contacted_at,
            DROP COLUMN IF EXISTS closed_at
    """)
