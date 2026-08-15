"""
Shared pytest fixtures.

The app talks to Postgres (Supabase) only — there is no SQLite fallback
and no per-test temp database file anymore (see app/db/database.py).
`test_database` therefore provides isolation by truncating every
application table before and after each test that requests it, rather
than by swapping in a throwaway SQLite file. This runs against whatever
BSTM_DATABASE_URL points at, so point it at a dev/test Supabase project
(or schema) — not a database you care about — before running the suite.
"""

import os

import pytest

from app.db.database import get_connection


# Ordered so FK-dependent tables are listed; TRUNCATE ... CASCADE below
# means the exact order doesn't actually matter, but keeping it roughly
# leaf-to-root makes the list easier to reason about.
_TABLES = [
    "activity",
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
    connection = get_connection()
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
    """Truncates all app tables before and after the test for isolation.

    Requires BSTM_DATABASE_URL to be set to a real Postgres connection —
    skips (rather than failing) if it isn't, since there's no local
    SQLite fallback to use instead.
    """

    if not os.getenv("BSTM_DATABASE_URL"):
        pytest.skip(
            "BSTM_DATABASE_URL is not set — tests require a live "
            "Postgres connection (point it at a dev/test database)."
        )

    _truncate_all()
    try:
        yield
    finally:
        _truncate_all()
