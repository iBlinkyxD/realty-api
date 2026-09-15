"""add status+created_at index to listings

Revision ID: u9v0w1x2y3z4
Revises: t8u9v0w1x2y3
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'u9v0w1x2y3z4'
down_revision = 't8u9v0w1x2y3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_listings_status_created_at "
        "ON listings (status, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_listings_status_created_at;")
