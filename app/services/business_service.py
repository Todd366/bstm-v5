import json

import psycopg2

from app.core.errors import Conflict
from app.core.validation import clean_text, require_uuid
from app.db.database import transaction


def create_business(
    name,
    owner,
    sector,
    location,
    main_problem,
):
    """Creates a business profile. Returns the new business's UUID (str).

    A business is identified by name + location (two shops can share a
    name in different villages)."""

    name = clean_text(name, "Business name", 150)
    owner = clean_text(owner, "Owner", 120)
    sector = clean_text(sector, "Sector", 100)
    location = clean_text(location, "Location", 120)
    main_problem = clean_text(main_problem, "Main problem", 1000)

    try:
        with transaction() as db:

            existing = db.execute(
                """
                SELECT id
                FROM businesses
                WHERE lower(name) = lower(?) AND lower(location) = lower(?)
                """,
                (name, location),
            ).fetchone()

            if existing:
                raise Conflict("This business is already registered at that location")

            row = db.execute(
                """
                INSERT INTO businesses (
                    name, owner, sector, location, main_problem
                )
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                """,
                (name, owner, sector, location, main_problem),
            ).fetchone()

            business_id = row["id"]

            db.execute(
                """
                INSERT INTO activity (event, actor_id, target_id, details)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "business_activated",
                    business_id,
                    business_id,
                    json.dumps({"sector": sector, "location": location}),
                ),
            )

    except psycopg2.errors.UniqueViolation:
        raise Conflict("This business is already registered at that location")

    return str(business_id)


def get_business(business_id):

    business_id = require_uuid(business_id, "Business")

    with transaction() as db:

        row = db.execute(
            "SELECT * FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

    if not row:
        raise ValueError("Business not found")

    return dict(row)


def list_businesses(limit=50, offset=0):

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    with transaction() as db:

        rows = db.execute(
            """
            SELECT * FROM businesses
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]


def set_audit_status(business_id, status):

    business_id = require_uuid(business_id, "Business")

    if status not in ("Pending", "InProgress", "Completed"):
        raise ValueError(f"Invalid audit_status: {status}")

    with transaction() as db:

        row = db.execute(
            """
            UPDATE businesses
            SET audit_status = ?, updated_at = now()
            WHERE id = ?
            RETURNING id
            """,
            (status, business_id),
        ).fetchone()

        if not row:
            raise ValueError("Business not found")

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "business_audit_status",
                business_id,
                business_id,
                json.dumps({"status": status}),
            ),
        )

    return get_business(business_id)
