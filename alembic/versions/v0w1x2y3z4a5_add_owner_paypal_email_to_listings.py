"""add owner_paypal_email to listings

Revision ID: v0w1x2y3z4a5
Revises: u9v0w1x2y3z4
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'v0w1x2y3z4a5'
down_revision = 'u9v0w1x2y3z4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('listings', sa.Column('owner_paypal_email', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('listings', 'owner_paypal_email')
