"""add verification rate limit columns

Revision ID: c1e5f8a2d934
Revises: b3d3d4b931c8
Create Date: 2026-06-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c1e5f8a2d934'
down_revision: Union[str, Sequence[str], None] = 'b3d3d4b931c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_attempts INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_code_sent_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_code_sent_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_attempts")
