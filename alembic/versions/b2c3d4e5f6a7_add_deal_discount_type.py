"""add_deal_discount_type

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # listings: rename deal_discount_pct → deal_discount_value (if old name still exists)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'deal_discount_pct'
            ) THEN
                ALTER TABLE listings RENAME COLUMN deal_discount_pct TO deal_discount_value;
            END IF;
        END $$;
    """)
    # Ensure column exists with correct precision (no-op if create_all already made it)
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS deal_discount_value NUMERIC(12,2)")
    op.execute("ALTER TABLE listings ALTER COLUMN deal_discount_value TYPE NUMERIC(12,2)")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS deal_discount_type TEXT NOT NULL DEFAULT 'pct'")

    # deal_requests: rename discount_pct → discount_value (if old name still exists)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'deal_requests' AND column_name = 'discount_pct'
            ) THEN
                ALTER TABLE deal_requests RENAME COLUMN discount_pct TO discount_value;
            END IF;
        END $$;
    """)
    op.execute("ALTER TABLE deal_requests ADD COLUMN IF NOT EXISTS discount_value NUMERIC(12,2)")
    op.execute("ALTER TABLE deal_requests ALTER COLUMN discount_value TYPE NUMERIC(12,2)")
    op.execute("ALTER TABLE deal_requests ADD COLUMN IF NOT EXISTS discount_type TEXT NOT NULL DEFAULT 'pct'")


def downgrade() -> None:
    op.execute("ALTER TABLE deal_requests DROP COLUMN IF EXISTS discount_type")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'deal_requests' AND column_name = 'discount_value'
            ) THEN
                ALTER TABLE deal_requests RENAME COLUMN discount_value TO discount_pct;
            END IF;
        END $$;
    """)
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS deal_discount_type")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'deal_discount_value'
            ) THEN
                ALTER TABLE listings RENAME COLUMN deal_discount_value TO deal_discount_pct;
            END IF;
        END $$;
    """)
