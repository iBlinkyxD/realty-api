"""add password reset fields

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-06-29

"""
from alembic import op
import sqlalchemy as sa

revision = 'n2o3p4q5r6s7'
down_revision = 'm1n2o3p4q5r6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('password_reset_token', sa.Text(), nullable=True))
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'], unique=True)
    op.add_column('users', sa.Column('password_reset_expires', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade():
    op.drop_index('ix_users_password_reset_token', table_name='users')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'password_reset_expires')
