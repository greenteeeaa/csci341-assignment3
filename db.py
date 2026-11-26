"""Shared database helpers for Part 2 (part2_queries.py) and Part 3 (app.py).

The connection string is read from the DATABASE_URL environment variable, e.g.
    postgresql+psycopg2://postgres:postgres@localhost:5432/conference_db
Hosting providers often hand out URLs that start with postgres:// or
postgresql://; they are normalised to the psycopg2 driver automatically.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/conference_db"


def normalize_database_url(url: str) -> str:
    """Make provider URLs usable by SQLAlchemy 2.x with the psycopg2 driver."""
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_engine(url: str | None = None, echo: bool = False) -> Engine:
    """Create the SQLAlchemy engine used by every script in the project."""
    raw_url = url or os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
    return create_engine(normalize_database_url(raw_url), echo=echo, pool_pre_ping=True)


def read_sql(file_name: str) -> str:
    """Return the text of one of the SQL scripts in the sql/ folder."""
    return (SQL_DIR / file_name).read_text(encoding="utf-8")


def run_script(conn: Connection, script: str) -> None:
    """Execute a multi-statement SQL script on an open SQLAlchemy connection.

    no_parameters=True makes SQLAlchemy call cursor.execute(script) without a
    parameter collection, so the script is sent to PostgreSQL unchanged.
    """
    result = conn.exec_driver_sql(script, execution_options={"no_parameters": True})
    result.close()
