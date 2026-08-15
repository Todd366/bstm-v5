"""
Postgres (Supabase) database layer.

Replaces the original SQLite layer. Schema lives in the `activation`
Postgres schema (see migration: activation_core_schema). Services get
a connection whose cursor returns dict-like rows (RealDictRow), so
existing row["field"] access patterns from the SQLite version keep
working unchanged.
"""

from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from app.core.config import DATABASE_URL, DB_SCHEMA


def get_connection():

    if not DATABASE_URL:
        raise RuntimeError(
            "BSTM_DATABASE_URL is not set. Point it at the Supabase "
            "pooler connection string (port 6543) in production, or "
            "the direct connection string for local development."
        )

    # connect_timeout bounds how long we wait for the TCP handshake itself.
    # statement_timeout bounds how long a query runs once Postgres has it.
    # keepalives make the OS proactively probe the connection and detect a
    # silently-dropped socket (common on mobile networks, e.g. a carrier
    # NAT timeout with no RST sent) within seconds instead of hanging
    # forever waiting on a response that will never arrive. statement_timeout
    # alone can't fix this case: if the request never reliably reached
    # Postgres, or its response never made it back, there's no query for
    # Postgres to cancel.
    connection = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=5,
        keepalives_interval=2,
        keepalives_count=2,
    )

    with connection.cursor() as cur:
        cur.execute(f"SET search_path TO {DB_SCHEMA}, public")
        cur.execute("SET statement_timeout = 15000")
    connection.commit()

    return connection


@contextmanager
def transaction():

    connection = get_connection()

    try:
        yield ExecuteAdapter(connection)
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


class _CursorResult:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class ExecuteAdapter:
    """Wraps a psycopg2 connection so db.execute(sql, params) works the
    same way it did against sqlite3.Connection, translating SQLite-style
    `?` placeholders to Postgres-style `%s` automatically."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, query, params=()):
        cursor = self._connection.cursor()
        translated = query.replace("?", "%s")
        cursor.execute(translated, params)
        return _CursorResult(cursor)

    def executescript(self, script):
        cursor = self._connection.cursor()
        cursor.execute(script)
        return _CursorResult(cursor)


def initialize_database():
    """No-op in Postgres: schema is managed by Supabase migrations,
    not created at app startup. Kept for compatibility with main.py."""
    return True
