from app.core.config import (
    APP_NAME,
    APP_VERSION,
    ENVIRONMENT
)

from app.db.database import (
    get_connection
)


def system_health():

    with get_connection() as db:

        db.execute(
            "SELECT 1"
        ).fetchone()

        youth = db.execute(
            "SELECT COUNT(*) FROM youth"
        ).fetchone()[0]

        businesses = db.execute(
            "SELECT COUNT(*) FROM businesses"
        ).fetchone()[0]

        opportunities = db.execute(
            "SELECT COUNT(*) FROM opportunities"
        ).fetchone()[0]

        trials = db.execute(
            "SELECT COUNT(*) FROM trials"
        ).fetchone()[0]

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
            "trials": trials
        }
    }
