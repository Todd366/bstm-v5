import hashlib
import random

from app.core.errors import RateLimitExceeded
from app.db.database import transaction


DEFAULT_LIMIT = 5
DEFAULT_WINDOW_MINUTES = 60

# Cleanup is opportunistic (inline, on a small fraction of checks)
# rather than a scheduled job.
CLEANUP_PROBABILITY = 0.02
CLEANUP_AGE_HOURS = 24


def hash_key(value):
    """Rate-limit keys derived from personal data (an email) are hashed
    so the table never stores them in clear."""

    return "h:" + hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:32]


def check_rate_limit(key, endpoint, limit=DEFAULT_LIMIT, window_minutes=DEFAULT_WINDOW_MINUTES):
    """Raises ValueError if `key` (an IP, or hash_key(...) of an
    account) has hit `limit` events for `endpoint` within the window;
    otherwise records this event. Call BEFORE the action being limited.
    """

    if not key:
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
            (key, endpoint, window_minutes),
        ).fetchone()["n"]

        if recent_count >= limit:
            raise RateLimitExceeded(
                "Too many requests — please wait a few minutes and try again."
            )

        db.execute(
            "INSERT INTO rate_limit_events (ip, endpoint) VALUES (?, ?)",
            (key, endpoint),
        )

        if random.random() < CLEANUP_PROBABILITY:
            db.execute(
                "DELETE FROM rate_limit_events WHERE created_at < now() - make_interval(hours => ?)",
                (CLEANUP_AGE_HOURS,),
            )
