"""Applies the bundled SQL migrations from inside the app, so the database
can be updated from the staff console on a phone (no SQL editor needed).

Safety:
  * Only files shipped in migrations/ are ever run; nothing comes from a request.
  * Admin-key only (middleware); each file runs in its own transaction.
  * Migrations older than BASELINE_CUTOFF are assumed already applied
    (they were run by hand before this tracker existed) and are only
    recorded, never re-run.
  * Files are written to be re-runnable (IF NOT EXISTS / ON CONFLICT).
"""

import glob
import os

from app.core.config import DB_SCHEMA
from app.db.database import get_connection

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "migrations")
BASELINE_CUTOFF = "20261012000000"


def _files():
    return sorted(os.path.basename(f) for f in glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))


def _ensure_tracker(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('schema_migrations') AS t")
        exists = cur.fetchone()["t"] is not None

        if not exists:
            cur.execute(
                "CREATE TABLE schema_migrations (name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now(), note text)"
            )
            cur.execute("ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY")
            for name in _files():
                if name < BASELINE_CUTOFF:
                    cur.execute(
                        "INSERT INTO schema_migrations (name, note) VALUES (%s, 'assumed applied before tracking') ON CONFLICT DO NOTHING",
                        (name,),
                    )
    conn.commit()


def _applied(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM schema_migrations")
        return {r["name"] for r in cur.fetchall()}


def status():
    conn = get_connection()
    try:
        _ensure_tracker(conn)
        done = _applied(conn)
    finally:
        conn.close()

    return {"applied": sorted(done), "pending": [f for f in _files() if f not in done]}


def apply_pending():
    """Runs every pending migration in order. Stops at the first failure
    (that file is rolled back) and reports which one failed."""

    conn = get_connection()
    ran = []

    try:
        _ensure_tracker(conn)
        done = _applied(conn)

        for name in _files():
            if name in done:
                continue

            with open(os.path.join(MIGRATIONS_DIR, name), encoding="utf-8") as fh:
                sql_text = fh.read()

            if DB_SCHEMA != "activation":
                sql_text = sql_text.replace("activation.", DB_SCHEMA + ".")

            try:
                with conn.cursor() as cur:
                    cur.execute(sql_text)
                    cur.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (name,))
                conn.commit()
            except Exception as exc:  # noqa: BLE001 - report which file failed
                conn.rollback()
                raise RuntimeError("Migration %s failed: %s" % (name, str(exc).strip().splitlines()[0][:200]))

            ran.append(name)
    finally:
        conn.close()

    return {"applied_now": ran, "pending": status()["pending"]}
