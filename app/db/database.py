"""
Postgres (Supabase) database layer.

Schema lives in the `activation` Postgres schema (see migrations/).
Services get a connection whose cursor returns dict-like rows
(RealDictRow) and call `db.execute(sql, params)` with `?` placeholders.
"""

import re
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2 import sql

from app.core.config import DATABASE_URL, DB_SCHEMA

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")

STATEMENT_TIMEOUT_MS = 15000


def get_connection():

    if not DATABASE_URL:
        raise RuntimeError(
            "BSTM_DATABASE_URL is not set. Point it at the Supabase "
            "session pooler connection string (port 5432)."
        )

    if not _IDENTIFIER.match(DB_SCHEMA):
        raise RuntimeError("BSTM_DB_SCHEMA is not a valid identifier")

    # connect_timeout bounds the TCP handshake. keepalives make the OS
    # detect a silently dropped socket (common on mobile networks and
    # carrier NAT) within seconds instead of hanging.
    connection = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=5,
        keepalives_interval=2,
        keepalives_count=2,
    )

    # If anything fails after the socket is open, close it: a leaked
    # connection holds one of the session pooler's few client slots,
    # which this app shares with other projects on the same database.
    try:
        with connection.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "SET search_path TO {}, public; "
                    "SET statement_timeout = {}"
                ).format(
                    sql.Identifier(DB_SCHEMA),
                    sql.Literal(STATEMENT_TIMEOUT_MS),
                )
            )
        connection.commit()
    except Exception:
        connection.close()
        raise

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


def ping():
    """Opens a connection, runs SELECT 1, closes it. Raises on any
    failure — callers decide how to report it."""

    connection = get_connection()

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1 AS one")
            cur.fetchone()
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
    """Wraps a psycopg2 connection so db.execute(sql, params) accepts
    `?` placeholders. Literal `%` characters in the SQL (LIKE patterns,
    format strings) are escaped first so they can never collide with
    psycopg2's own %s substitution."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, query, params=()):
        cursor = self._connection.cursor()
        translated = query.replace("%", "%%").replace("?", "%s")
        cursor.execute(translated, params)
        return _CursorResult(cursor)


def initialize_database():
    """No-op: schema is managed by migrations, not created at startup."""
    return True
