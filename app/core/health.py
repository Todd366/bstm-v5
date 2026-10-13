import logging

from app.core.config import APP_NAME, APP_VERSION, ENVIRONMENT
from app.db.database import ping, transaction

logger = logging.getLogger("bstm")


def database_status():
    """Returns (ok, error_type, error_message). Never raises."""

    try:
        ping()
        return True, None, None
    except Exception as exc:  # noqa: BLE001 — a health check must not raise
        return False, type(exc).__name__, str(exc).strip().replace("\n", " ")[:300]


def liveness():
    """Public health payload: reveals nothing beyond status."""

    ok, error_type, error_message = database_status()

    if not ok:
        # First thing in the log line, so truncated log viewers still
        # show the cause.
        logger.error("database check failed: %s: %s", error_type, error_message)

    return ok, {
        "status": "ok" if ok else "degraded",
        "service": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "database": "ok" if ok else "error",
        **({} if ok else {"error_type": error_type}),
    }, error_message


def system_health():
    """Admin-only: adds row counts."""

    with transaction() as db:

        youth = db.execute("SELECT COUNT(*) AS count FROM youth").fetchone()["count"]
        businesses = db.execute(
            "SELECT COUNT(*) AS count FROM businesses"
        ).fetchone()["count"]
        opportunities = db.execute(
            "SELECT COUNT(*) AS count FROM opportunities"
        ).fetchone()["count"]
        trials = db.execute("SELECT COUNT(*) AS count FROM trials").fetchone()["count"]

    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "database": "ok",
        "counts": {
            "youth": youth,
            "businesses": businesses,
            "opportunities": opportunities,
            "trials": trials,
        },
    }
