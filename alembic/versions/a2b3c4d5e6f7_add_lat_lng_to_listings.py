"""add_lat_lng_to_listings

Revision ID: a2b3c4d5e6f7
Revises: f4a6b8c2d0e1
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f4a6b8c2d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('latitude', sa.Numeric(10, 7), nullable=True))
    op.add_column('listings', sa.Column('longitude', sa.Numeric(10, 7), nullable=True))


def downgrade() -> None:
    op.drop_column('listings', 'longitude')
    op.drop_column('listings', 'latitude')
