"""Create (or re-create) the database objects and load the seed data.

Usage
    python init_db.py              # DROP + CREATE all tables, load seed data, create the view
    python init_db.py --if-empty   # do the above only if the tables do not exist yet
                                   # (used by the deployment start command)

The connection string comes from DATABASE_URL (see db.py).
Running this script is the quickest way to restore the initial dataset.
"""
from __future__ import annotations

import argparse

from sqlalchemy import text
from sqlalchemy.engine import Engine

from db import get_engine, read_sql, run_script


def tables_exist(engine: Engine) -> bool:
    with engine.connect() as conn:
        return bool(conn.execute(text("SELECT to_regclass('public.app_user') IS NOT NULL")).scalar())


def init_database(engine: Engine) -> None:
    """Schema, seed data and view in ONE transaction (all or nothing)."""
    with engine.begin() as conn:
        run_script(conn, read_sql("schema.sql"))
        run_script(conn, read_sql("seed.sql"))
        run_script(conn, read_sql("view.sql"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--if-empty", action="store_true",
                        help="only initialise when the tables do not exist yet")
    parser.add_argument("--database-url", help="overrides the DATABASE_URL environment variable")
    args = parser.parse_args()

    engine = get_engine(args.database_url)
    if args.if_empty and tables_exist(engine):
        print("Tables already exist - nothing to do.")
        return
    init_database(engine)
    print("Database created and populated with the seed data (view accepted_paper_schedule included).")


if __name__ == "__main__":
    main()
