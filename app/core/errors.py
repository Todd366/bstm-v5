"""Typed service errors. All subclass ValueError so existing callers and
tests that expect ValueError keep working; the API layer uses the
subclass to choose the HTTP status."""


class Conflict(ValueError):
    """Resource already exists / state does not allow the action → 409."""


class RateLimitExceeded(ValueError):
    """Too many requests → 429."""


class Forbidden(ValueError):
    """Authenticated, but not allowed → 403."""
