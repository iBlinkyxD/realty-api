"""add_view_count_and_updated_at

Revision ID: f4a6b8c2d0e1
Revises: c1e5f8a2d934
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a6b8c2d0e1'
down_revision: Union[str, Sequence[str], None] = 'c1e5f8a2d934'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('view_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('listings', sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_column('listings', 'updated_at')
    op.drop_column('listings', 'view_count')
