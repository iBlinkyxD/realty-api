"""add settings table

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-06-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'l3m4n5o6p7q8'
down_revision = 'k2l3m4n5o6p7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('data', JSONB(), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('id = 1', name='settings_single_row'),
    )
    op.execute("INSERT INTO settings (id, data) VALUES (1, '{}') ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_table('settings')
