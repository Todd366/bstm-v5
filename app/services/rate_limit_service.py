import random

from app.db.database import transaction


# Registrations are one-time actions for a real person — a handful per
# hour comfortably covers someone retrying a typo, while still
# blocking a script from spamming the endpoint. Same limit for both
# public write endpoints; revisit independently if usage patterns
# diverge once there's real traffic to observe.
DEFAULT_LIMIT = 5
DEFAULT_WINDOW_MINUTES = 60

# Cleanup is opportunistic (runs inline on a small random fraction of
# checks) rather than a scheduled job, to avoid needing separate cron
# infrastructure for a single early-stage feature. 1-in-50 requests is
# frequent enough to keep the table small at this traffic level
# without adding meaningful latency to any individual request.
CLEANUP_PROBABILITY = 0.02
CLEANUP_AGE_HOURS = 24


def check_rate_limit(ip, endpoint, limit=DEFAULT_LIMIT, window_minutes=DEFAULT_WINDOW_MINUTES):
    """Raises ValueError if `ip` has hit `limit` requests to `endpoint`
    within the last `window_minutes`; otherwise records this request
    and returns normally. Call this BEFORE performing the action being
    limited, not after.
    """

    if not ip:
        # No IP to key on (shouldn't normally happen) — fail safe by
        # not blocking, rather than accidentally rate-limiting every
        # request under a single "unknown" bucket.
        return

    with transaction() as db:

        recent_count = db.execute(
            """
            SELECT count(*) AS n
            FROM rate_limit_events
            WHERE ip = ?
              AND endpoint = ?
              AND created_at > now() - make_interval(mins => ?)
            """,
            (ip, endpoint, window_minutes),
        ).fetchone()["n"]

        if recent_count >= limit:
            raise ValueError(
                f"Too many requests — please wait before trying again."
            )

        db.execute(
            "INSERT INTO rate_limit_events (ip, endpoint) VALUES (?, ?)",
            (ip, endpoint),
        )

        if random.random() < CLEANUP_PROBABILITY:
            db.execute(
                "DELETE FROM rate_limit_events WHERE created_at < now() - make_interval(hours => ?)",
                (CLEANUP_AGE_HOURS,),
            )
