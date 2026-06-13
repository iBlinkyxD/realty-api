"""add_activity_log_table

Revision ID: e2f3a4b5c6d7
Revises: d5e6f7a8b9c0, f4a6b8c2d0e1
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = ('d5e6f7a8b9c0', 'f4a6b8c2d0e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            actor_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_log_created_at ON activity_log (created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_activity_log_created_at")
    op.execute("DROP TABLE IF EXISTS activity_log")
