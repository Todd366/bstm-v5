import os

import pytest

from app.db.database import get_connection, transaction


def test_connection_can_run_a_query():
    """Confirms BSTM_DATABASE_URL is set and Postgres is reachable."""

    if not os.getenv("BSTM_DATABASE_URL"):
        pytest.skip("BSTM_DATABASE_URL is not set")

    connection = get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1 AS one")
            result = cur.fetchone()

        assert result["one"] == 1

    finally:
        connection.close()


def test_transaction_commits_and_rolls_back():
    """The `transaction()` context manager should roll back if the
    block raises, and not propagate anything but the original error."""

    if not os.getenv("BSTM_DATABASE_URL"):
        pytest.skip("BSTM_DATABASE_URL is not set")

    with transaction() as db:
        result = db.execute("SELECT 1 AS one").fetchone()
        assert result["one"] == 1

    with pytest.raises(RuntimeError):
        with transaction() as db:
            db.execute("SELECT 1")
            raise RuntimeError("forcing a rollback")
