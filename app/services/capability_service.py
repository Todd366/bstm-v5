import json

import psycopg2

from app.core.errors import Conflict
from app.core.validation import clean_text, require_uuid
from app.db.database import transaction


ALLOWED_LEVELS = (
    "Beginner",
    "Developing",
    "Intermediate",
    "Advanced",
    "Expert",
)


def create_capability(name, category, description=None):

    name = clean_text(name, "Capability name", 100)
    category = clean_text(category, "Capability category", 60)
    description = clean_text(description, "Description", 500, required=False)

    try:
        with transaction() as db:

            row = db.execute(
                """
                INSERT INTO capabilities (name, category, description)
                VALUES (?, ?, ?)
                RETURNING id
                """,
                (name, category, description),
            ).fetchone()

            capability_id = row["id"]

    except psycopg2.errors.UniqueViolation:
        raise Conflict("Capability already exists")

    return str(capability_id)


def assign_capability_to_youth(youth_id, capability_id, level="Beginner"):

    youth_id = require_uuid(youth_id, "Youth")
    capability_id = require_uuid(capability_id, "Capability")

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
                            "capability_id": capability_id,
                            "capability_name": capability["name"],
                            "level": level,
                        }
                    ),
                ),
            )

    except psycopg2.errors.UniqueViolation:
        raise Conflict("Capability already assigned to youth")

    return str(youth_capability_id)


def verify_capability(youth_capability_id, verified=True):
    """CLAIMED -> VERIFIED step: rows start unverified; only this
    explicit (admin) action changes it."""

    youth_capability_id = require_uuid(youth_capability_id, "Youth capability")

    with transaction() as db:

        row = db.execute(
            """
            UPDATE youth_capabilities
            SET verified = ?
            WHERE id = ?
            RETURNING id, youth_id, capability_id, level, verified
            """,
            (bool(verified), youth_capability_id),
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


def list_capabilities(category=None):
    """The catalog of capabilities a youth can claim."""

    with transaction() as db:

        if category:
            rows = db.execute(
                """
                SELECT id, name, category, description, created_at
                FROM capabilities
                WHERE lower(category) = lower(?)
                ORDER BY name ASC
                """,
                (category,),
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT id, name, category, description, created_at
                FROM capabilities
                ORDER BY category ASC, name ASC
                """
            ).fetchall()

    return [dict(row) for row in rows]


def list_youth_capabilities(youth_id):

    youth_id = require_uuid(youth_id, "Youth")

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
