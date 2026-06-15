"""add_listing_media_and_rent_fields

Revision ID: a3b4c5d6e7f8
Revises: f4a6b8c2d0e1
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS video_links TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS tour_3d_url TEXT")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS utilities TEXT")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS included_utilities TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS association_fee NUMERIC(12,2)")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS deposit_policy TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS deposit_policy")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS association_fee")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS included_utilities")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS utilities")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS tour_3d_url")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS video_links")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS tags")
