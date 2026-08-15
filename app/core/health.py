from app.core.config import APP_NAME, APP_VERSION, ENVIRONMENT
from app.db.database import transaction


def system_health():

    with transaction() as db:

        db.execute("SELECT 1").fetchone()

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
