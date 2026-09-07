"""add share_image_url to listings

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-09-07

"""
from alembic import op

revision = 'o3p4q5r6s7t8'
down_revision = 'n2o3p4q5r6s7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE listings
            ADD COLUMN IF NOT EXISTS share_image_url TEXT;
    """)


def downgrade():
    op.drop_column('listings', 'share_image_url')
