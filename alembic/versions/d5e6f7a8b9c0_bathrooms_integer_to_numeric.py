"""bathrooms_integer_to_numeric

Revision ID: d5e6f7a8b9c0
Revises: b1c2d3e4f5a6
Create Date: 2026-06-11 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'listings', 'bathrooms',
        type_=sa.Numeric(3, 1),
        existing_type=sa.Integer(),
        postgresql_using='bathrooms::numeric(3,1)',
    )


def downgrade() -> None:
    op.alter_column(
        'listings', 'bathrooms',
        type_=sa.Integer(),
        existing_type=sa.Numeric(3, 1),
        postgresql_using='bathrooms::integer',
    )
