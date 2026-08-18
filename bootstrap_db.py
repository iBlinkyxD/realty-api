"""
Create the base tables on an empty database, so `alembic upgrade head` has
something to migrate.

No migration in `alembic/versions/` creates the core tables — the oldest one
(`434d4c5bb8b6`) already assumes `users` exists and only adds columns to it.
Historically the schema came from `Base.metadata.create_all()`, with migrations
layering changes on top; that call was later lost, which left the API unable to
start against a brand-new database:

    psycopg2.errors.UndefinedTable: relation "users" does not exist

This runs before Alembic and only ever touches a genuinely empty database. On
an existing one it is a no-op, so deploys against a live DB are unaffected.

Note this creates tables *without* stamping a revision — the migration chain
still runs afterwards, because some schema exists only there and not in the
models (e.g. the `users_user_code_seq` sequence and the DEFAULT that assigns
`user_code`). Stamping instead of migrating would silently skip all of that.
"""

import logging

from sqlalchemy import inspect

from database import Base, engine
import models  # noqa: F401  — registers every model on Base.metadata

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("bootstrap_db")


def main() -> None:
    inspector = inspect(engine)

    if inspector.has_table("alembic_version"):
        log.info("Database is already under Alembic control — nothing to bootstrap.")
        return

    existing = inspector.get_table_names()
    if existing:
        # Tables but no alembic_version: an unmanaged DB. Creating anything here
        # risks a schema that does not match its real migration state, and
        # guessing which revision it is on would be worse. Leave it alone.
        log.warning(
            "Found %d table(s) but no alembic_version — leaving the schema alone. "
            "Run `alembic stamp <revision>` to bring it under Alembic control.",
            len(existing),
        )
        return

    log.info("Empty database — creating %d base tables.", len(Base.metadata.tables))
    Base.metadata.create_all(bind=engine)
    log.info("Base tables created. Alembic will now apply the migration chain.")


if __name__ == "__main__":
    main()
