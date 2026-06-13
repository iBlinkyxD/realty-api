"""add_listing_fields

Revision ID: b3d3d4b931c8
Revises: 434d4c5bb8b6
Create Date: 2026-06-09 14:46:02.055387

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b3d3d4b931c8'
down_revision: Union[str, Sequence[str], None] = '434d4c5bb8b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS lot_size_sqft INTEGER")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS roi NUMERIC(5,2)")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS seller_financing BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS hoa BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS hoa_fee NUMERIC(10,2)")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS tax_exempt BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS gated_community BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS construction_status TEXT")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS year_built INTEGER")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS features TEXT[] DEFAULT '{}'")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS maps_url TEXT")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS tag TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS tag")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS maps_url")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS features")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS year_built")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS construction_status")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS gated_community")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS tax_exempt")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS hoa_fee")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS hoa")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS seller_financing")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS roi")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS lot_size_sqft")
