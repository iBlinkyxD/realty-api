"""add assigned_realtor_id to users

Revision ID: q5r6s7t8u9v0
Revises: p4q5r6s7t8u9
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'q5r6s7t8u9v0'
down_revision = 'p4q5r6s7t8u9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column(
            'assigned_realtor_id',
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_assigned_realtor_id ON users (assigned_realtor_id)")


def downgrade():
    op.drop_index('ix_users_assigned_realtor_id', table_name='users')
    op.drop_column('users', 'assigned_realtor_id')
