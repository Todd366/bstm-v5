import itertools
import uuid

from app.services import youth_service

_counter = itertools.count(1)


def _is_valid_uuid(value):
    """True if `value` parses as a UUID (any version)."""

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def create_youth(**kwargs):
    """youth_service.create_youth with a unique email and a valid
    password filled in unless the test supplies its own."""

    n = next(_counter)
    kwargs.setdefault("email", f"youth{n}-{uuid.uuid4().hex[:6]}@example.com")
    kwargs.setdefault("password", "correct-horse-battery")
    kwargs.setdefault("location", "Gaborone")
    kwargs.setdefault("goal", "Build skills")

    return youth_service.create_youth(**kwargs)
