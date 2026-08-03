import json

from app.core.ids import generate_id
from app.core.time import utc_now
from app.db.database import transaction


def create_capability(
    name,
    category,
    description=None
):

    if not name or not name.strip():
        raise ValueError(
            "Capability name is required"
        )

    if not category or not category.strip():
        raise ValueError(
            "Capability category is required"
        )

    with transaction() as db:

        existing = db.execute(
            """
            SELECT id
            FROM capabilities
            WHERE LOWER(name) = LOWER(?)
            """,
            (
                name.strip(),
            )
        ).fetchone()

        if existing:

            raise ValueError(
                "Capability already exists"
            )

        capability_id = generate_id(
            "CAP"
        )

        created_at = utc_now()

        db.execute(
            """
            INSERT INTO capabilities (
                id,
                name,
                category,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                capability_id,
                name.strip(),
                category.strip(),
                description.strip()
                if description
                else None,
                created_at
            )
        )

    return capability_id


def assign_capability_to_youth(
    youth_id,
    capability_id,
    level="Beginner"
):

    if not youth_id:
        raise ValueError(
            "Youth ID is required"
        )

    if not capability_id:
        raise ValueError(
            "Capability ID is required"
        )

    allowed_levels = [
        "Beginner",
        "Developing",
        "Intermediate",
        "Advanced",
        "Expert"
    ]

    if level not in allowed_levels:

        raise ValueError(
            "Invalid capability level"
        )

    with transaction() as db:

        youth = db.execute(
            """
            SELECT
                id,
                name
            FROM youth
            WHERE id = ?
            """,
            (
                youth_id,
            )
        ).fetchone()

        if not youth:

            raise ValueError(
                "Youth not found"
            )

        capability = db.execute(
            """
            SELECT
                id,
                name
            FROM capabilities
            WHERE id = ?
            """,
            (
                capability_id,
            )
        ).fetchone()

        if not capability:

            raise ValueError(
                "Capability not found"
            )

        existing = db.execute(
            """
            SELECT id
            FROM youth_capabilities
            WHERE youth_id = ?
            AND capability_id = ?
            """,
            (
                youth_id,
                capability_id
            )
        ).fetchone()

        if existing:

            raise ValueError(
                "Capability already assigned to youth"
            )

        youth_capability_id = generate_id(
            "YC"
        )

        created_at = utc_now()

        db.execute(
            """
            INSERT INTO youth_capabilities (
                id,
                youth_id,
                capability_id,
                level,
                verified,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                youth_capability_id,
                youth_id,
                capability_id,
                level,
                0,
                created_at
            )
        )

        db.execute(
            """
            INSERT INTO activity (
                id,
                event,
                actor_id,
                target_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "capability_assigned",
                youth_id,
                youth_capability_id,
                json.dumps({
                    "youth_id": youth_id,
                    "youth_name": youth["name"],
                    "capability_id": capability_id,
                    "capability_name": capability["name"],
                    "level": level
                }),
                created_at
            )
        )

    return youth_capability_id


def list_capabilities():

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                id,
                name,
                category,
                description,
                created_at
            FROM capabilities
            ORDER BY name ASC
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def list_youth_capabilities(
    youth_id
):

    if not youth_id:
        raise ValueError(
            "Youth ID is required"
        )

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
            JOIN capabilities c
                ON c.id = yc.capability_id
            WHERE yc.youth_id = ?
            ORDER BY yc.created_at DESC
            """,
            (
                youth_id,
            )
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]
