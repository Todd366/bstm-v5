import json

import psycopg2

from app.db.database import transaction


def create_business(
    name,
    owner,
    sector,
    location,
    main_problem,
):
    """Creates a business profile. Returns the new business's UUID (as str)."""

    try:
        with transaction() as db:

            existing = db.execute(
                """
                SELECT id
                FROM businesses
                WHERE lower(name) = lower(?)
                """,
                (name.strip(),),
            ).fetchone()

            if existing:
                raise ValueError("Business already exists")

            row = db.execute(
                """
                INSERT INTO businesses (
                    name, owner, sector, location, main_problem
                )
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    name.strip(),
                    owner.strip(),
                    sector.strip(),
                    location.strip(),
                    main_problem.strip(),
                ),
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
                    json.dumps({"name": name, "sector": sector}),
                ),
            )

    except psycopg2.errors.UniqueViolation:
        raise ValueError("Business already exists")

    return str(business_id)


def get_business(business_id):

    with transaction() as db:

        row = db.execute(
            "SELECT * FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

    return dict(row) if row else None


def list_businesses(limit=50, offset=0):

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

    if status not in ("Pending", "InProgress", "Completed"):
        raise ValueError(f"Invalid audit_status: {status}")

    with transaction() as db:

        db.execute(
            """
            UPDATE businesses
            SET audit_status = ?, updated_at = now()
            WHERE id = ?
            """,
            (status, business_id),
        )

    return get_business(business_id)
