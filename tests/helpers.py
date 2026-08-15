import uuid


def _is_valid_uuid(value):
    """True if `value` parses as a UUID (any version) — used to confirm
    IDs returned by the service layer are real Postgres UUIDs, not the
    old SQLite-era prefixed string IDs (e.g. 'OP-0001')."""

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False
