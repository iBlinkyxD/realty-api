"""bathrooms_integer_to_numeric

Revision ID: d5e6f7a8b9c0
Revises: b1c2d3e4f5a6
Create Date: 2026-06-11 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'bathrooms'
                AND data_type = 'integer'
            ) THEN
                ALTER TABLE listings ALTER COLUMN bathrooms TYPE NUMERIC(3,1) USING bathrooms::numeric(3,1);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'bathrooms'
                AND data_type = 'numeric'
            ) THEN
                ALTER TABLE listings ALTER COLUMN bathrooms TYPE INTEGER USING bathrooms::integer;
            END IF;
        END $$;
    """)
