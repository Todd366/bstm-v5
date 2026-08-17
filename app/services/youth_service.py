import json

import psycopg2
import psycopg2.extras

from app.db.database import transaction


def create_youth(
    name,
    location,
    goal,
    passion=None,
    availability=None,
    equipment=None,
    intake=None,
):
    """Creates a youth profile. Returns the new youth's UUID (as str).

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

    try:
        with transaction() as db:

            existing = db.execute(
                """
                SELECT id
                FROM youth
                WHERE lower(name) = lower(?)
                """,
                (name.strip(),),
            ).fetchone()

            if existing:
                raise ValueError("Youth profile already exists")

            row = db.execute(
                """
                INSERT INTO youth (
                    name, location, passion, goal, availability, equipment, intake
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
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

    return dict(row)


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
