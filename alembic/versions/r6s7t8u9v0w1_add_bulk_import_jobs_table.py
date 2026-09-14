"""add bulk_import_jobs table

Revision ID: r6s7t8u9v0w1
Revises: q5r6s7t8u9v0
Create Date: 2026-09-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'r6s7t8u9v0w1'
down_revision = 'q5r6s7t8u9v0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS bulk_import_jobs (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            status           TEXT NOT NULL DEFAULT 'pending',
            total_rows       INTEGER NOT NULL DEFAULT 0,
            processed_rows   INTEGER NOT NULL DEFAULT 0,
            succeeded_count  INTEGER NOT NULL DEFAULT 0,
            skipped_count    INTEGER NOT NULL DEFAULT 0,
            failed_count     INTEGER NOT NULL DEFAULT 0,
            results          JSONB NOT NULL DEFAULT '[]',
            created_by       UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at     TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_bulk_import_jobs_created_at ON bulk_import_jobs (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bulk_import_jobs")
