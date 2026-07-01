"""add rental prices colisting pdf calendly

Revision ID: o3p4q5r6s8t9
Revises: n2o3p4q5r6s7
Create Date: 2026-06-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'o3p4q5r6s8t9'
down_revision = 'n2o3p4q5r6s7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('price_per_day',   sa.Numeric(12, 2), nullable=True))
    op.add_column('listings', sa.Column('price_per_month', sa.Numeric(12, 2), nullable=True))
    op.add_column('listings', sa.Column('co_listing_agreement_accepted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('listings', sa.Column('co_listing_agreement_url',      sa.Text(),    nullable=True))
    op.add_column('users',    sa.Column('calendly_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('listings', 'price_per_day')
    op.drop_column('listings', 'price_per_month')
    op.drop_column('listings', 'co_listing_agreement_accepted')
    op.drop_column('listings', 'co_listing_agreement_url')
    op.drop_column('users',    'calendly_url')
