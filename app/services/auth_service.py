"""
Real youth authentication: password hashing + JWT session tokens.

Password hashing uses stdlib hashlib.pbkdf2_hmac rather than
bcrypt/argon2 — deliberately, given how much trouble this project has
already had tonight with C-extension dependencies that don't compile
cleanly on Termux (ARM, ships without a full toolchain) or need care
on Vercel's build environment. PBKDF2-HMAC-SHA256 with a high
iteration count is still a real, standard, non-reversible password
hash — not a shortcut, just a dependency-free one.

JWTs use PyJWT, which IS a new dependency, but it's pure Python (no C
extension) and the industry-standard approach — rolling a custom
signed-token scheme by hand is a worse trade than adding one small,
well-audited library for something this security-sensitive.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import JWT_SECRET

PBKDF2_ITERATIONS = 260_000
TOKEN_LIFETIME = timedelta(days=30)


def hash_password(password):
    """Returns a string encoding both the salt and hash, so verification
    doesn't need the salt stored in a separate column."""

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password, stored_hash):
    """Constant-time comparison — avoids leaking timing information
    about how much of the hash matched."""

    try:
        algorithm, iterations, salt, digest = stored_hash.split("$")
        iterations = int(iterations)
    except (ValueError, AttributeError):
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()

    return hmac.compare_digest(candidate, digest)


def create_access_token(youth_id):
    if not JWT_SECRET:
        raise RuntimeError("BSTM_JWT_SECRET is not set — cannot issue tokens.")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(youth_id),
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_access_token(token):
    """Returns the youth_id encoded in a valid token, or None if the
    token is missing, malformed, expired, or signed with a different
    secret. Callers treat None as "not authenticated" — this
    deliberately never raises for a bad token, only for
    misconfiguration (no JWT_SECRET set)."""

    if not JWT_SECRET:
        raise RuntimeError("BSTM_JWT_SECRET is not set — cannot verify tokens.")

    if not token:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None
