"""add brokerage email phone drop agent contact

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s8t9
Create Date: 2026-06-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'p4q5r6s7t8u9'
down_revision = 'o3p4q5r6s8t9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('listings', sa.Column('co_listing_brokerage_email', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('co_listing_brokerage_phone', sa.Text(), nullable=True))
    op.drop_column('listings', 'co_listing_agent_contact')


def downgrade():
    op.add_column('listings', sa.Column('co_listing_agent_contact', sa.Text(), nullable=True))
    op.drop_column('listings', 'co_listing_brokerage_phone')
    op.drop_column('listings', 'co_listing_brokerage_email')
