"""add_listing_edits_table

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PGEnum

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Using PGEnum with create_type=False so op.create_table never tries to emit
# CREATE TYPE — we handle that ourselves below with the DO block.
edit_status_col = PGEnum(
    'pending', 'approved', 'rejected',
    name='listing_edit_status',
    create_type=False,
)


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE listing_edit_status AS ENUM ('pending', 'approved', 'rejected');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.create_table(
        'listing_edits',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('listing_id', UUID(as_uuid=True), sa.ForeignKey('listings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('submitted_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('proposed_data', JSONB, nullable=False),
        sa.Column('status', edit_status_col, nullable=False, server_default='pending'),
        sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('reviewed_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('listing_edits')
    op.execute("DROP TYPE IF EXISTS listing_edit_status")
