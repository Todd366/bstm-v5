import json

import psycopg2
import psycopg2.extras

from app.core.config import RATE_LOGIN_PER_15MIN_ACCOUNT
from app.core.errors import Conflict
from app.core.validation import (
    check_json_size,
    clean_email,
    clean_phone,
    split_login_id,
    clean_text,
    require_uuid,
)
from app.db.database import transaction
from app.services.auth_service import (
    burn_verification_time,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from app.services.rate_limit_service import check_rate_limit, hash_key

ALLOWED_LEVELS = ("Beginner", "Developing", "Intermediate", "Advanced", "Expert")
MAX_REGISTRATION_CAPABILITIES = 12

# Columns safe to return to a client. password_hash never leaves the
# service layer.
_PROFILE_COLUMNS = """
    id, name, location, passion, goal, availability, equipment,
    level, capability_score, learning_score, reputation_score,
    reliability_score, completed_trials, completed_opportunities,
    revenue, email, phone, must_change_password, intake, bio, public_profile, created_at, updated_at
"""

# List views leave out the questionnaire answers (financial position,
# obstacles): bulk listings should not carry sensitive free-form data.
_LIST_COLUMNS = _PROFILE_COLUMNS.replace("intake,", "")


def create_youth(
    name,
    location,
    goal,
    email=None,
    password=None,
    passion=None,
    availability=None,
    equipment=None,
    intake=None,
    capabilities=None,
    phone=None,
):
    """Creates a youth profile. Returns the new youth's UUID (str).

    Names are NOT unique — two real people can share a name. Identity is
    the email address.

    `capabilities` is an optional list of {"capability_id", "level"}
    from the catalog, claimed (unverified) in the same transaction so a
    new youth has something for matching to work with immediately.

    `intake` is the frontend's free-form questionnaire answers, stored
    as JSONB and never inspected here.
    """

    name = clean_text(name, "Name", 120)
    location = clean_text(location, "Location", 120)
    goal = clean_text(goal, "Goal", 200)
    passion = clean_text(passion, "Passion", 300, required=False)
    availability = clean_text(availability, "Availability", 100, required=False)
    equipment = clean_text(equipment, "Equipment", 300, required=False)
    email = clean_email(email) if email else None
    phone = clean_phone(phone) if phone else None
    if not email and not phone:
        raise ValueError("Enter an email address or a phone number")
    validate_password(password)
    check_json_size(intake, "Intake")

    claims = _clean_capability_claims(capabilities)

    try:
        with transaction() as db:

            if email and db.execute("SELECT id FROM youth WHERE lower(email) = lower(?)", (email,)).fetchone():
                raise Conflict("An account with this email already exists")

            if phone and db.execute("SELECT id FROM youth WHERE phone = ?", (phone,)).fetchone():
                raise Conflict("An account with this phone number already exists")

            row = db.execute(
                """
                INSERT INTO youth (
                    name, location, passion, goal, availability, equipment,
                    intake, email, phone, password_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    name,
                    location,
                    passion,
                    goal,
                    availability,
                    equipment,
                    psycopg2.extras.Json(intake) if intake else None,
                    email,
                    phone,
                    hash_password(password),
                ),
            ).fetchone()

            youth_id = row["id"]

            for capability_id, level in claims:
                db.execute(
                    """
                    INSERT INTO youth_capabilities (youth_id, capability_id, level, verified)
                    SELECT ?, c.id, ?, false
                    FROM capabilities c
                    WHERE c.id = ?
                    ON CONFLICT (youth_id, capability_id) DO NOTHING
                    """,
                    (youth_id, level, capability_id),
                )

            db.execute(
                """
                INSERT INTO activity (event, actor_id, target_id, details)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "youth_activated",
                    youth_id,
                    youth_id,
                    json.dumps({"location": location, "capabilities": len(claims)}),
                ),
            )

    except psycopg2.errors.UniqueViolation:
        raise Conflict("An account with this email or phone number already exists")

    return str(youth_id)


def _clean_capability_claims(capabilities):
    if not capabilities:
        return []

    if not isinstance(capabilities, (list, tuple)):
        raise ValueError("Capabilities must be a list")

    claims = {}

    for item in capabilities[:MAX_REGISTRATION_CAPABILITIES]:

        if not isinstance(item, dict):
            raise ValueError("Each capability must have a capability_id and level")

        capability_id = require_uuid(item.get("capability_id"), "Capability")
        level = item.get("level") or "Beginner"

        if level not in ALLOWED_LEVELS:
            raise ValueError("Invalid capability level")

        claims[capability_id] = level

    return list(claims.items())


def authenticate_youth(email, password):
    """Returns the youth's UUID (str) for a correct email/password,
    otherwise raises ValueError("Invalid email or password"). The same
    message — and the same CPU cost — whether the email exists or not."""

    if not isinstance(email, str) or not isinstance(password, str):
        raise ValueError("Invalid email or password")

    email = email.strip()

    if not email or not password or len(password) > 128 or len(email) > 254:
        raise ValueError("Invalid email or password")

    try:
        kind, ident = split_login_id(email)
    except ValueError:
        burn_verification_time(password)
        raise ValueError("Invalid email or password")

    # Per-account throttle: stops password guessing against one account
    # even when attempts come from many addresses.
    check_rate_limit(
        hash_key(ident), "login-account", RATE_LOGIN_PER_15MIN_ACCOUNT, 15
    )

    with transaction() as db:

        row = db.execute(
            "SELECT id, password_hash FROM youth WHERE "
            + ("lower(email) = lower(?)" if kind == "email" else "phone = ?"),
            (ident,),
        ).fetchone()

        if not row or not row["password_hash"]:
            burn_verification_time(password)
            raise ValueError("Invalid email or password")

        if not verify_password(password, row["password_hash"]):
            raise ValueError("Invalid email or password")

        if needs_rehash(row["password_hash"]):
            db.execute(
                "UPDATE youth SET password_hash = ? WHERE id = ?",
                (hash_password(password), row["id"]),
            )

    return str(row["id"])


def get_youth(youth_id):
    """Full profile of one youth (never includes password_hash)."""

    youth_id = require_uuid(youth_id, "Youth")

    with transaction() as db:

        row = db.execute(
            f"SELECT {_PROFILE_COLUMNS} FROM youth WHERE id = ?",
            (youth_id,),
        ).fetchone()

    if not row:
        raise ValueError("Youth not found")

    return dict(row)


def list_youth(limit=50, offset=0):

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    with transaction() as db:

        rows = db.execute(
            f"""
            SELECT {_LIST_COLUMNS}
            FROM youth
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(row) for row in rows]


def change_password(youth_id, current, new):
    """Own password change. Needs the current password (a stolen token alone
    cannot lock the person out); clears the agent's temporary-password flag."""

    youth_id = require_uuid(youth_id, "Youth")

    if not isinstance(current, str) or not isinstance(new, str):
        raise ValueError("Enter your current and new password")

    validate_password(new)
    check_rate_limit(hash_key("pw:" + youth_id), "change-password", 10, 15)

    with transaction() as db:
        row = db.execute("SELECT password_hash FROM youth WHERE id = ? FOR UPDATE", (youth_id,)).fetchone()

        if not row or not row["password_hash"] or not verify_password(current, row["password_hash"]):
            raise ValueError("Your current password is not right")

        if current == new:
            raise ValueError("Choose a different new password")

        db.execute(
            "UPDATE youth SET password_hash = ?, must_change_password = false WHERE id = ?",
            (hash_password(new), youth_id),
        )

    return {"status": "password_changed"}
