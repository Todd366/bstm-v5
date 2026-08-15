import json

import psycopg2

from app.db.database import transaction


ALLOWED_LEVELS = (
    "Beginner",
    "Developing",
    "Intermediate",
    "Advanced",
    "Expert",
)


def create_capability(name, category, description=None):

    if not name or not name.strip():
        raise ValueError("Capability name is required")

    if not category or not category.strip():
        raise ValueError("Capability category is required")

    try:
        with transaction() as db:

            row = db.execute(
                """
                INSERT INTO capabilities (name, category, description)
                VALUES (?, ?, ?)
                RETURNING id
                """,
                (
                    name.strip(),
                    category.strip(),
                    description.strip() if description else None,
                ),
            ).fetchone()

            capability_id = row["id"]

    except psycopg2.errors.UniqueViolation:
        raise ValueError("Capability already exists")

    return str(capability_id)


def assign_capability_to_youth(youth_id, capability_id, level="Beginner"):

    if not youth_id:
        raise ValueError("Youth ID is required")

    if not capability_id:
        raise ValueError("Capability ID is required")

    if level not in ALLOWED_LEVELS:
        raise ValueError("Invalid capability level")

    try:
        with transaction() as db:

            youth = db.execute(
                "SELECT id, name FROM youth WHERE id = ?",
                (youth_id,),
            ).fetchone()

            if not youth:
                raise ValueError("Youth not found")

            capability = db.execute(
                "SELECT id, name FROM capabilities WHERE id = ?",
                (capability_id,),
            ).fetchone()

            if not capability:
                raise ValueError("Capability not found")

            row = db.execute(
                """
                INSERT INTO youth_capabilities (
                    youth_id, capability_id, level, verified
                )
                VALUES (?, ?, ?, false)
                RETURNING id
                """,
                (youth_id, capability_id, level),
            ).fetchone()

            youth_capability_id = row["id"]

            db.execute(
                """
                INSERT INTO activity (event, actor_id, target_id, details)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "capability_assigned",
                    youth_id,
                    youth_capability_id,
                    json.dumps(
                        {
                            "youth_id": youth_id,
                            "youth_name": youth["name"],
                            "capability_id": capability_id,
                            "capability_name": capability["name"],
                            "level": level,
                        }
                    ),
                ),
            )

    except psycopg2.errors.UniqueViolation:
        raise ValueError("Capability already assigned to youth")

    return str(youth_capability_id)


def verify_capability(youth_capability_id, verified=True):
    """Marks a claimed capability as verified (or reverts to unverified).

    This is the CLAIMED -> VERIFIED epistemic step: capability rows start
    unverified on assignment, and only become verified through an explicit
    action here (e.g. a business confirming a trial result, or an
    assessment being scored). Calling code decides what counts as
    verification evidence — this function just records the outcome.
    """

    with transaction() as db:

        row = db.execute(
            """
            UPDATE youth_capabilities
            SET verified = ?
            WHERE id = ?
            RETURNING id, youth_id, capability_id, level, verified
            """,
            (verified, youth_capability_id),
        ).fetchone()

        if not row:
            raise ValueError("Youth capability not found")

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "capability_verified" if verified else "capability_unverified",
                row["youth_id"],
                youth_capability_id,
                json.dumps({"capability_id": str(row["capability_id"])}),
            ),
        )

    return dict(row)


def list_capabilities():

    with transaction() as db:

        rows = db.execute(
            """
            SELECT id, name, category, description, created_at
            FROM capabilities
            ORDER BY name ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def list_youth_capabilities(youth_id):

    if not youth_id:
        raise ValueError("Youth ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                yc.id,
                yc.youth_id,
                yc.capability_id,
                c.name AS capability_name,
                c.category,
                c.description,
                yc.level,
                yc.verified,
                yc.created_at
            FROM youth_capabilities yc
            JOIN capabilities c ON c.id = yc.capability_id
            WHERE yc.youth_id = ?
            ORDER BY yc.created_at DESC
            """,
            (youth_id,),
        ).fetchall()

    return [dict(row) for row in rows]
