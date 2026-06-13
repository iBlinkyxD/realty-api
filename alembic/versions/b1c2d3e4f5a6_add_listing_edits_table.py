"""add_listing_edits_table

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE listing_edit_status AS ENUM ('pending', 'approved', 'rejected');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS listing_edits (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
            submitted_by UUID NOT NULL REFERENCES users(id),
            proposed_data JSONB NOT NULL,
            status listing_edit_status NOT NULL DEFAULT 'pending',
            submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            reviewed_by UUID REFERENCES users(id),
            reviewed_at TIMESTAMPTZ,
            rejection_reason TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_listing_edits_listing_id ON listing_edits (listing_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_listing_edits_listing_id")
    op.execute("DROP TABLE IF EXISTS listing_edits")
    op.execute("DROP TYPE IF EXISTS listing_edit_status")
