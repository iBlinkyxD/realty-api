"""add email verification columns to users

Revision ID: 434d4c5bb8b6
Revises:
Create Date: 2026-06-08 16:42:19.220507

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '434d4c5bb8b6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_code TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_code_expires_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_code_expires_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_code")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
