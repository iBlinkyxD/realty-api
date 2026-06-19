"""add listing_events table

Revision ID: f7a8b9c0d1e2
Revises: a3b4c5d6e7f8
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = 'f7a8b9c0d1e2'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS listing_events (
            id              UUID DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
            listing_id      UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
            event_type      TEXT NOT NULL,
            actor_id        UUID REFERENCES users(id) ON DELETE SET NULL,
            note            TEXT,
            snapshot_before JSONB,
            snapshot_after  JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_listing_events_listing_id
        ON listing_events (listing_id)
    """)


def downgrade():
    op.drop_index('ix_listing_events_listing_id', table_name='listing_events')
    op.drop_table('listing_events')
