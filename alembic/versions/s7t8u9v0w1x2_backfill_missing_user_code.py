"""backfill user_code for users left NULL by the pre-a414125 ORM bug

Revision ID: s7t8u9v0w1x2
Revises: r6s7t8u9v0w1
Create Date: 2026-09-14

Before commit a414125, SQLAlchemy sent an explicit NULL for user_code on every
insert, silently overriding the column's DB-side DEFAULT. Accounts created
between the original user_code backfill and that fix landing have no code.
Existing non-NULL codes (some of which are already referenced externally,
e.g. a co-listing partner's CSV keys off assigned_agent_id) are left
untouched — NULL rows are assigned the next available numbers in join order,
then the sequence is advanced past the new max.

"""
from alembic import op

revision = 's7t8u9v0w1x2'
down_revision = 'r6s7t8u9v0w1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        WITH base AS (
            SELECT COALESCE(MAX(user_code), 0) AS max_code FROM users
        ),
        ordered AS (
            SELECT id, row_number() OVER (ORDER BY created_at ASC) AS rn
            FROM users
            WHERE user_code IS NULL
        )
        UPDATE users
        SET user_code = base.max_code + ordered.rn
        FROM ordered, base
        WHERE users.id = ordered.id;
    """)
    op.execute("""
        SELECT setval(
            'users_user_code_seq',
            COALESCE((SELECT MAX(user_code) FROM users), 0) + 1,
            false
        );
    """)


def downgrade() -> None:
    pass  # data backfill — not reversible
