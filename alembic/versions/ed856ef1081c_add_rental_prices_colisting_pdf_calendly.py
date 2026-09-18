"""add rental prices colisting pdf calendly

Revision ID: ed856ef1081c
Revises: u9v0w1x2y3z4
Create Date: 2026-06-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'ed856ef1081c'
down_revision = 'u9v0w1x2y3z4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent on purpose: production already has these columns (they were applied outside
    # Alembic before this revision existed), so a plain ADD COLUMN would abort the deploy.
    op.add_column('listings', sa.Column('price_per_day',   sa.Numeric(12, 2), nullable=True), if_not_exists=True)
    op.add_column('listings', sa.Column('price_per_month', sa.Numeric(12, 2), nullable=True), if_not_exists=True)
    op.add_column('listings', sa.Column('co_listing_agreement_accepted', sa.Boolean(), nullable=False, server_default='false'), if_not_exists=True)
    op.add_column('listings', sa.Column('co_listing_agreement_url',      sa.Text(),    nullable=True), if_not_exists=True)
    op.add_column('users',    sa.Column('calendly_url', sa.Text(), nullable=True), if_not_exists=True)


def downgrade() -> None:
    op.drop_column('listings', 'price_per_day', if_exists=True)
    op.drop_column('listings', 'price_per_month', if_exists=True)
    op.drop_column('listings', 'co_listing_agreement_accepted', if_exists=True)
    op.drop_column('listings', 'co_listing_agreement_url', if_exists=True)
    op.drop_column('users',    'calendly_url', if_exists=True)
