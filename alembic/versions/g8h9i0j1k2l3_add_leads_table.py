"""add leads table

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'g8h9i0j1k2l3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            type                TEXT NOT NULL,
            name                TEXT NOT NULL,
            email               TEXT NOT NULL,
            phone               TEXT,
            message             TEXT,
            property_id         UUID REFERENCES listings(id) ON DELETE SET NULL,
            from_user_id        UUID REFERENCES users(id) ON DELETE SET NULL,
            assigned_realtor_id UUID REFERENCES users(id) ON DELETE SET NULL,
            status              TEXT NOT NULL DEFAULT 'new',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_status ON leads (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_assigned_realtor_id ON leads (assigned_realtor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_from_user_id ON leads (from_user_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS leads")
