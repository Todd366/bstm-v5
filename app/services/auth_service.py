"""
Youth authentication: password hashing + JWT session tokens.

Password hashing uses stdlib hashlib.pbkdf2_hmac (no C-extension
dependency — bcrypt/argon2 do not build cleanly on Termux). The
iteration count is stored inside each hash, so it can be raised later
and old hashes are upgraded transparently at next login
(see needs_rehash).

JWTs use PyJWT (pure Python).
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import JWT_SECRET

PBKDF2_ITERATIONS = 600_000
MAX_PASSWORD_LENGTH = 128
MIN_PASSWORD_LENGTH = 8
TOKEN_LIFETIME = timedelta(days=14)
JWT_ISSUER = "bstm-activation"

_dummy_hash = None


def validate_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters")


def hash_password(password, iterations=None):
    """Returns a string encoding algorithm, iterations, salt and hash."""

    iterations = iterations or PBKDF2_ITERATIONS
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password, stored_hash):
    """Constant-time comparison."""

    try:
        algorithm, iterations, salt, digest = stored_hash.split("$")
        iterations = int(iterations)
    except (ValueError, AttributeError):
        return False

    if algorithm != "pbkdf2_sha256" or iterations < 1 or iterations > 5_000_000:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()

    return hmac.compare_digest(candidate, digest)


def needs_rehash(stored_hash):
    try:
        return int(stored_hash.split("$")[1]) < PBKDF2_ITERATIONS
    except (IndexError, ValueError, AttributeError):
        return True


def burn_verification_time(password):
    """Spends the same CPU as a real verification. Called when the email
    is unknown so response time does not reveal which emails exist."""

    global _dummy_hash

    if _dummy_hash is None:
        _dummy_hash = hash_password("not-a-real-password")

    verify_password(password if isinstance(password, str) else "", _dummy_hash)


def create_access_token(youth_id):
    if not JWT_SECRET:
        raise RuntimeError("BSTM_JWT_SECRET is not set — cannot issue tokens.")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(youth_id),
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_access_token(token):
    """Returns the youth_id in a valid token, or None if the token is
    missing, malformed, expired or signed with a different secret.
    Raises RuntimeError only for misconfiguration (no JWT_SECRET)."""

    if not JWT_SECRET:
        raise RuntimeError("BSTM_JWT_SECRET is not set — cannot verify tokens.")

    if not token:
        return None

    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=["HS256"], issuer=JWT_ISSUER
        )
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None
