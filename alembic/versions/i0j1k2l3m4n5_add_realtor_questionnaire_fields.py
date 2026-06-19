"""add realtor questionnaire fields to upgrade_requests

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-06-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'i0j1k2l3m4n5'
down_revision = 'h9i0j1k2l3m4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("upgrade_requests", sa.Column("years_experience", sa.Integer(), nullable=True))
    op.add_column("upgrade_requests", sa.Column("specialties", sa.Text(), nullable=True))
    op.add_column("upgrade_requests", sa.Column("bio", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("upgrade_requests", "bio")
    op.drop_column("upgrade_requests", "specialties")
    op.drop_column("upgrade_requests", "years_experience")
