"""Staff accounts: individual logins with a role, so every money or
approval action is attributable to a person (not a shared key)."""

import psycopg2

from app.core.config import OWNER_EMAIL, RATE_LOGIN_PER_15MIN_ACCOUNT
from app.core.errors import Conflict
from app.core.validation import clean_email, clean_text, require_uuid
from app.db.database import transaction
from app.services.auth_service import (
    burn_verification_time,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from app.services.rate_limit_service import check_rate_limit, hash_key

ROLES = ("admin", "finance", "field", "support")


def create_staff(name, email, password, role):
    name = clean_text(name, "Name", 120)
    email = clean_email(email)
    validate_password(password)

    if role not in ROLES:
        raise ValueError("Role must be one of: " + ", ".join(ROLES))

    if email.lower() == OWNER_EMAIL:
        role = "admin"   # the owner is recognised by email, not by this role

    try:
        with transaction() as db:
            row = db.execute(
                "INSERT INTO staff (name, email, password_hash, role) VALUES (?, ?, ?, ?) RETURNING id",
                (name, email, hash_password(password), role),
            ).fetchone()
            db.execute(
                "INSERT INTO activity (event, actor_id, target_id, details) VALUES ('staff_created', NULL, ?, '{}')",
                (row["id"],),
            )
    except psycopg2.errors.UniqueViolation:
        raise Conflict("A staff member with that email already exists")

    return str(row["id"])


def list_staff():
    with transaction() as db:
        rows = db.execute(
            "SELECT id, name, email, role, active, created_at, last_login_at FROM staff ORDER BY created_at"
        ).fetchall()

    out = [dict(r) for r in rows]
    for r in out:
        if r["email"].lower() == OWNER_EMAIL:
            r["role"] = "owner"
    return out


def set_staff_active(staff_id, active, acting_id=None):
    staff_id = require_uuid(staff_id, "Staff member")

    if not active and acting_id and str(acting_id) == staff_id:
        raise ValueError("You cannot deactivate your own account")

    with transaction() as db:
        if not active:
            target = db.execute("SELECT role, email FROM staff WHERE id = ? FOR UPDATE", (staff_id,)).fetchone()
            if target and target["email"].lower() == OWNER_EMAIL:
                raise Conflict("The owner account cannot be turned off")
            if target and target["role"] == "admin":
                others = db.execute(
                    "SELECT count(*) AS n FROM staff WHERE role = 'admin' AND active AND id <> ?", (staff_id,)
                ).fetchone()["n"]
                if others == 0:
                    raise Conflict("At least one active admin must remain")

        row = db.execute("UPDATE staff SET active = ? WHERE id = ? RETURNING id", (bool(active), staff_id)).fetchone()

        if not row:
            raise ValueError("Staff member not found")

    return {"id": staff_id, "active": bool(active)}


def set_staff_password(staff_id, new_password):
    staff_id = require_uuid(staff_id, "Staff member")
    validate_password(new_password)

    with transaction() as db:
        row = db.execute(
            "UPDATE staff SET password_hash = ? WHERE id = ? RETURNING id", (hash_password(new_password), staff_id)
        ).fetchone()

        if not row:
            raise ValueError("Staff member not found")

    return {"id": staff_id, "status": "password_changed"}


def authenticate_staff(email, password):
    """Same guarantees as the other logins: one error message, equal CPU
    cost, per-account throttle. Returns {id, name, role}."""

    bad = ValueError("Invalid email or password")

    if not isinstance(email, str) or not isinstance(password, str):
        raise bad

    email = email.strip()

    if not email or not password or len(password) > 128 or len(email) > 254:
        raise bad

    check_rate_limit(hash_key("staff:" + email.lower()), "login-account", RATE_LOGIN_PER_15MIN_ACCOUNT, 15)

    with transaction() as db:
        row = db.execute(
            "SELECT id, name, role, active, password_hash FROM staff WHERE lower(email) = lower(?)", (email,)
        ).fetchone()

        if not row or not row["active"]:
            burn_verification_time(password)
            raise bad

        if not verify_password(password, row["password_hash"]):
            raise bad

        if needs_rehash(row["password_hash"]):
            db.execute("UPDATE staff SET password_hash = ? WHERE id = ?", (hash_password(password), row["id"]))

        db.execute("UPDATE staff SET last_login_at = now() WHERE id = ?", (row["id"],))

    is_owner = email.lower() == OWNER_EMAIL
    return {"id": str(row["id"]), "name": row["name"], "role": "owner" if is_owner else row["role"]}


def lookup_active_staff(staff_id):
    """Fresh name/role for a token's subject, or None if the account was
    deactivated (so removing someone takes effect immediately)."""

    try:
        staff_id = require_uuid(staff_id, "Staff member")
    except ValueError:
        return None

    with transaction() as db:
        row = db.execute("SELECT name, role, email FROM staff WHERE id = ? AND active", (staff_id,)).fetchone()

    return {"name": row["name"], "role": row["role"], "email": row["email"]} if row else None
