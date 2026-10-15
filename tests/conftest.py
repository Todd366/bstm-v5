"""
Shared pytest fixtures.

SAFETY: these tests NEVER touch the real `activation` schema. When
BSTM_DATABASE_URL is set, this module points the app at a brand-new,
throw-away schema (bstm_test_<random>) inside that database, builds it
from migrations/, and drops it when the run ends. Truncation only ever
runs inside such a schema (checked by name). Without BSTM_DATABASE_URL,
database tests are skipped and only the pure-logic tests run.
"""

import glob
import os
import re
import uuid

import pytest

_URL = os.getenv("BSTM_DATABASE_URL")
_SCHEMA = None

# Must happen before anything imports app.core.config.
os.environ.setdefault("BSTM_JWT_SECRET", "test-secret-test-secret-test-secret")
os.environ.setdefault("BSTM_API_KEY", "test-admin-key")

if _URL:
    _SCHEMA = "bstm_test_" + uuid.uuid4().hex[:8]
    os.environ["BSTM_DB_SCHEMA"] = _SCHEMA

from app.db import database  # noqa: E402  (after the env override above)

_MIGRATIONS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")


def _raw_connection():
    """A connection with NO search_path override, for schema setup."""

    import psycopg2

    return psycopg2.connect(_URL)


def _migration_sql():
    for path in sorted(glob.glob(os.path.join(_MIGRATIONS, "*.sql"))):
        if "access_policy" in path:
            continue  # references Supabase roles; irrelevant to a test schema
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        yield re.sub(r"\bactivation\b", _SCHEMA, text)


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    if not _URL:
        yield
        return

    connection = _raw_connection()
    try:
        with connection.cursor() as cur:
            for script in _migration_sql():
                cur.execute(script)
        connection.commit()

        yield
    finally:
        connection.rollback()
        with connection.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE")
        connection.commit()
        connection.close()


_TABLES = [
    "rate_limit_events",
    "field_audits",
    "activity",
    "evidence",
    "opportunity_matches",
    "trials",
    "opportunity_assignments",
    "youth_capabilities",
    "capabilities",
    "opportunities",
    "businesses",
    "youth",
]


def _truncate_all():
    assert _SCHEMA and _SCHEMA.startswith("bstm_test_"), "refusing to truncate a non-test schema"

    connection = database.get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE"
            )
        connection.commit()
    finally:
        connection.close()


@pytest.fixture
def test_database():
    """Empty tables in the throw-away schema before and after the test."""

    if not _URL:
        pytest.skip(
            "BSTM_DATABASE_URL is not set — database tests need a Postgres "
            "connection (a temporary schema is created and dropped for you)."
        )

    _truncate_all()
    try:
        yield
    finally:
        _truncate_all()
