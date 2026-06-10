"""add verification rate limit columns

Revision ID: c1e5f8a2d934
Revises: b3d3d4b931c8
Create Date: 2026-06-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1e5f8a2d934'
down_revision: Union[str, Sequence[str], None] = 'b3d3d4b931c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('verification_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('last_code_sent_at', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_code_sent_at')
    op.drop_column('users', 'verification_attempts')
