"""Small, dependency-free input validators shared by services.

Every function raises ValueError with a message safe to show to a user.
"""

import json
import re
import uuid
from urllib.parse import urlparse

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")


def clean_text(value, label, max_length, required=True):
    """Strips, enforces presence and length. Returns None for empty
    optional values."""

    if value is None:
        value = ""

    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")

    value = value.strip()

    if not value:
        if required:
            raise ValueError(f"{label} is required")
        return None

    if len(value) > max_length:
        raise ValueError(f"{label} must be at most {max_length} characters")

    return value


def clean_email(value):
    value = clean_text(value, "Email", 254)

    if not _EMAIL.match(value):
        raise ValueError("A valid email is required")

    return value


def clean_phone(value):
    """Botswana numbers only, stored as +267XXXXXXXX (8 digits starting 3-7).
    Accepts 71234567, 071234567, 26771234567, +267 71 234 567."""

    digits = re.sub(r"[^0-9]", "", str(value or ""))

    if digits.startswith("267") and len(digits) == 11:
        digits = digits[3:]
    elif digits.startswith("0") and len(digits) == 9:
        digits = digits[1:]

    if not re.fullmatch(r"[3-7][0-9]{7}", digits):
        raise ValueError("Enter a Botswana phone number like 71 234 567")

    return "+267" + digits


def split_login_id(value):
    """('email', cleaned) when it has an @, otherwise ('phone', +267...)."""

    value = str(value or "").strip()

    if "@" in value:
        return "email", clean_email(value)

    return "phone", clean_phone(value)


def require_uuid(value, label):
    """Returns the canonical string form of a UUID or raises ValueError
    whose message contains 'not found' so the API maps it to 404 (an id
    that is not even a UUID cannot exist)."""

    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ValueError(f"{label} not found")


def clean_url(value, label="URL"):
    """Only http(s) URLs: anything else (javascript:, data:) becomes an
    XSS vector the moment a client renders it as a link."""

    value = clean_text(value, label, 2000, required=False)

    if value is None:
        return None

    parsed = urlparse(value)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"{label} must start with http:// or https://")

    return value


def check_json_size(value, label, max_bytes=20000):
    if value is None:
        return None

    try:
        encoded = json.dumps(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be valid JSON")

    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"{label} is too large")

    return value
