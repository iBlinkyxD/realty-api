"""add_view_count_and_updated_at

Revision ID: f4a6b8c2d0e1
Revises: c1e5f8a2d934
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f4a6b8c2d0e1'
down_revision: Union[str, Sequence[str], None] = 'c1e5f8a2d934'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()")


def downgrade() -> None:
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS view_count")
