"""add_deal_of_week

Revision ID: a1b2c3d4e5f6
Revises: e2f3a4b5c6d7
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE deal_request_status AS ENUM ('pending', 'approved', 'rejected');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_deal BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS deal_discount_pct NUMERIC(5,2)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS deal_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            listing_id UUID NOT NULL REFERENCES listings(id),
            requested_by UUID NOT NULL REFERENCES users(id),
            discount_pct NUMERIC(5,2) NOT NULL,
            message TEXT,
            status deal_request_status NOT NULL DEFAULT 'pending',
            rejection_reason TEXT,
            reviewed_by UUID REFERENCES users(id),
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_deal_requests_listing_id ON deal_requests (listing_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_deal_requests_status ON deal_requests (status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_deal_requests_status")
    op.execute("DROP INDEX IF EXISTS ix_deal_requests_listing_id")
    op.execute("DROP TABLE IF EXISTS deal_requests")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS deal_discount_pct")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS is_deal")
    op.execute("DROP TYPE IF EXISTS deal_request_status")
