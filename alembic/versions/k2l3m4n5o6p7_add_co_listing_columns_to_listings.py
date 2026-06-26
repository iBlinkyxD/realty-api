"""add co_listing columns to listings

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa

revision = 'k2l3m4n5o6p7'
down_revision = 'j1k2l3m4n5o6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('co_listing_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('listings', sa.Column('co_listing_brokerage', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('co_listing_agent_name', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('co_listing_agent_contact', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('co_listing_commission_split', sa.Numeric(5, 2), nullable=True))
    op.add_column('listings', sa.Column('co_listing_notes', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('co_listing_status', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('listings', 'co_listing_status')
    op.drop_column('listings', 'co_listing_notes')
    op.drop_column('listings', 'co_listing_commission_split')
    op.drop_column('listings', 'co_listing_agent_contact')
    op.drop_column('listings', 'co_listing_agent_name')
    op.drop_column('listings', 'co_listing_brokerage')
    op.drop_column('listings', 'co_listing_enabled')
