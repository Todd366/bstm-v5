import json

import psycopg2
import psycopg2.extras

from app.db.database import transaction
from app.services.auth_service import hash_password, verify_password


def create_youth(
    name,
    location,
    goal,
    email,
    password,
    passion=None,
    availability=None,
    equipment=None,
    intake=None,
):
    """Creates a youth profile. Returns the new youth's UUID (as str).

    email/password are required — without them this registration would
    be a dead end with no way for the person to come back and prove
    it's them, which is what every trial/capability/opportunity screen
    in the product depends on. Existing pre-auth youth rows (created
    before this was required) keep working with a null email/password;
    they just can't log in until one is set.

    Note: `skills` is intentionally not accepted here — capabilities are
    normalized into activation.youth_capabilities (see capability_service),
    not stored as free text on the youth row. This is a deliberate
    departure from the legacy SQLite schema.

    `intake` is an optional free-form dict holding the frontend's full
    discovery-questionnaire response (life position, education,
    financial reality, obstacles, aspiration, etc.) — richer than this
    function's own named fields support. Stored as-is in the JSONB
    `intake` column; nothing in this function inspects its contents.
    """

    if not email or "@" not in email:
        raise ValueError("A valid email is required")

    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    try:
        with transaction() as db:

            existing_name = db.execute(
                """
                SELECT id
                FROM youth
                WHERE lower(name) = lower(?)
                """,
                (name.strip(),),
            ).fetchone()

            if existing_name:
                raise ValueError("Youth profile already exists")

            existing_email = db.execute(
                """
                SELECT id
                FROM youth
                WHERE lower(email) = lower(?)
                """,
                (email.strip(),),
            ).fetchone()

            if existing_email:
                raise ValueError("An account with this email already exists")

            row = db.execute(
                """
                INSERT INTO youth (
                    name, location, passion, goal, availability, equipment,
                    intake, email, password_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    name.strip(),
                    location.strip(),
                    passion.strip() if passion else None,
                    goal.strip(),
                    availability,
                    equipment,
                    psycopg2.extras.Json(intake) if intake else None,
                    email.strip(),
                    hash_password(password),
                ),
            ).fetchone()

            youth_id = row["id"]

            db.execute(
                """
                INSERT INTO activity (event, actor_id, target_id, details)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "youth_activated",
                    youth_id,
                    youth_id,
                    json.dumps({"name": name, "location": location}),
                ),
            )

    except psycopg2.errors.UniqueViolation:
        raise ValueError("Youth profile already exists")

    return str(youth_id)


def authenticate_youth(email, password):
    """Returns the youth's UUID (as str) if email/password match a real
    account, otherwise raises ValueError. Deliberately uses the same
    error message whether the email doesn't exist or the password is
    wrong — distinguishing the two would let someone probe which
    emails are registered."""

    if not email or not password:
        raise ValueError("Invalid email or password")

    with transaction() as db:

        row = db.execute(
            """
            SELECT id, password_hash
            FROM youth
            WHERE lower(email) = lower(?)
            """,
            (email.strip(),),
        ).fetchone()

    if not row or not row["password_hash"] or not verify_password(password, row["password_hash"]):
        raise ValueError("Invalid email or password")

    return str(row["id"])


def get_youth(youth_id):

    if not youth_id:
        raise ValueError("Youth ID is required")

    with transaction() as db:

        row = db.execute(
            "SELECT * FROM youth WHERE id = ?",
            (youth_id,),
        ).fetchone()

    if not row:
        raise ValueError("Youth not found")

    youth = dict(row)
    youth.pop("password_hash", None)
    return youth


def list_youth(limit=50, offset=0):

    with transaction() as db:

        rows = db.execute(
            """
            SELECT * FROM youth
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]
