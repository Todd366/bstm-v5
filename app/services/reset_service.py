"""Password reset without email/SMS: staff verify the person (phone call,
in person), create a one-time code, and tell it to them. The person then
sets their own new password with that code."""

import hashlib
import hmac
import secrets

from app.core.errors import Forbidden
from app.core.validation import clean_email, require_uuid, split_login_id
from app.db.database import transaction
from app.services.auth_service import hash_password, validate_password
from app.services.rate_limit_service import check_rate_limit, hash_key

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no 0/O/1/I/L: easy to read out loud
CODE_LENGTH = 8
CODE_HOURS = 24
MAX_ATTEMPTS = 5
TABLES = {"youth": "youth", "business": "businesses"}


def _hash(code):
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def _find(db, account_type, ident):
    """Youth can be found by email or phone; businesses by email."""
    kind, v = split_login_id(ident) if account_type == "youth" else ("email", clean_email(ident))
    where = "lower(email) = lower(?)" if kind == "email" else "phone = ?"
    return db.execute("SELECT id FROM " + TABLES[account_type] + " WHERE " + where, (v,)).fetchone()


def create_reset_code(account_type, email, created_by="staff"):
    if account_type not in TABLES:
        raise ValueError("Choose youth or business")

    with transaction() as db:
        account = _find(db, account_type, email)

        if not account:
            raise ValueError("Account not found")

        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))

        # Only the newest code works.
        db.execute(
            "UPDATE password_resets SET used_at = now() WHERE account_type = ? AND account_id = ? AND used_at IS NULL",
            (account_type, account["id"]),
        )
        db.execute(
            """
            INSERT INTO password_resets (account_type, account_id, code_hash, expires_at, created_by)
            VALUES (?, ?, ?, now() + make_interval(hours => ?), ?)
            """,
            (account_type, account["id"], _hash(code), CODE_HOURS, created_by),
        )
        db.execute(
            "INSERT INTO activity (event, actor_id, target_id, details) VALUES ('password_reset_issued', NULL, ?, ?)",
            (account["id"], '{"by": "%s", "type": "%s"}' % (created_by.replace('"', ""), account_type)),
        )

    return {"code": code, "expires_in_hours": CODE_HOURS}


def redeem_reset_code(account_type, email, code, new_password):
    """One generic failure message for every wrong input. A wrong guess is
    counted in its own committed transaction (raising inside the one that
    counts it would roll the count back)."""

    fail = Forbidden("That code is not valid or has expired. Ask BSTM for a new one.")

    if account_type not in TABLES or not isinstance(code, str) or not isinstance(email, str):
        raise fail

    validate_password(new_password)
    check_rate_limit(hash_key("reset:" + email.strip().lower()), "reset-account", 10, 60)

    wrong = False

    with transaction() as db:
        try:
            account = _find(db, account_type, email.strip())
        except ValueError:
            account = None

        reset = None

        if account:
            reset = db.execute(
                """
                SELECT id, code_hash, attempts FROM password_resets
                WHERE account_type = ? AND account_id = ? AND used_at IS NULL AND expires_at > now()
                ORDER BY created_at DESC LIMIT 1 FOR UPDATE
                """,
                (account_type, account["id"]),
            ).fetchone()

        if not reset or reset["attempts"] >= MAX_ATTEMPTS:
            wrong = True
        elif not hmac.compare_digest(reset["code_hash"], _hash(code)):
            db.execute("UPDATE password_resets SET attempts = attempts + 1 WHERE id = ?", (reset["id"],))
            wrong = True
        else:
            db.execute(
                "UPDATE " + TABLES[account_type] + " SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), account["id"]),
            )
            db.execute("UPDATE password_resets SET used_at = now() WHERE id = ?", (reset["id"],))

    if wrong:
        raise fail

    return {"status": "password_changed"}


def list_open_resets():
    with transaction() as db:
        rows = db.execute(
            """
            SELECT r.id, r.account_type, r.created_at, r.expires_at, r.created_by,
                   COALESCE(y.email, y.phone, b.email) AS email
            FROM password_resets r
            LEFT JOIN youth y ON r.account_type = 'youth' AND y.id = r.account_id
            LEFT JOIN businesses b ON r.account_type = 'business' AND b.id = r.account_id
            WHERE r.used_at IS NULL AND r.expires_at > now()
            ORDER BY r.created_at DESC LIMIT 50
            """
        ).fetchall()
    return [dict(r) for r in rows]
