"""add settings table

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-06-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'l3m4n5o6p7q8'
down_revision = 'k2l3m4n5o6p7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS so the chain can also run against a create_all-built schema
    op.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id         INTEGER PRIMARY KEY NOT NULL,
            data       JSONB NOT NULL DEFAULT '{}',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT settings_single_row CHECK (id = 1)
        );
    """)
    op.execute("INSERT INTO settings (id, data) VALUES (1, '{}') ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_table('settings')
