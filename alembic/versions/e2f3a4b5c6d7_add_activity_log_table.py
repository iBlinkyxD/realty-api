"""add_activity_log_table

Revision ID: e2f3a4b5c6d7
Revises: f4a6b8c2d0e1
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = ('d5e6f7a8b9c0', 'f4a6b8c2d0e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'activity_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('actor_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_activity_log_created_at', 'activity_log', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_activity_log_created_at', 'activity_log')
    op.drop_table('activity_log')
