import json

from app.core.departments import DEPARTMENTS
from app.core.ids import generate_id
from app.core.time import utc_now
from app.db.database import transaction


def create_opportunity(
    business_id,
    title,
    description=None,
    department=None,
    budget=0
):

    if not business_id:
        raise ValueError("Business ID is required")

    if not title or not title.strip():
        raise ValueError("Opportunity title is required")

    if department is not None and department not in DEPARTMENTS:
        raise ValueError("Invalid department")

    if budget is None:
        budget = 0

    if budget < 0:
        raise ValueError("Budget cannot be negative")

    with transaction() as db:

        business = db.execute(
            "SELECT id, name FROM businesses WHERE id = ?",
            (business_id,)
        ).fetchone()

        if not business:
            raise ValueError("Business not found")

        opportunity_id = generate_id("OP")
        created_at = utc_now()

        db.execute(
            """
            INSERT INTO opportunities (
                id, business_id, title, description,
                status, department, budget, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                business_id,
                title.strip(),
                description.strip() if description else None,
                "Open",
                department,
                budget,
                created_at
            )
        )

        db.execute(
            """
            UPDATE businesses
            SET opportunities_generated = opportunities_generated + 1
            WHERE id = ?
            """,
            (business_id,)
        )

        db.execute(
            """
            INSERT INTO activity (
                id, event, actor_id, target_id, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "opportunity_created",
                business_id,
                opportunity_id,
                json.dumps({
                    "business_id": business_id,
                    "business_name": business["name"],
                    "title": title.strip(),
                    "department": department,
                    "budget": budget
                }),
                created_at
            )
        )

    return opportunity_id


def list_opportunities():

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                o.id, o.business_id, b.name AS business_name,
                o.title, o.description, o.status,
                o.department, o.budget, o.created_at
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            ORDER BY o.created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_opportunity(
    opportunity_id
):

    if not opportunity_id:
        raise ValueError("Opportunity ID is required")

    with transaction() as db:

        row = db.execute(
            """
            SELECT
                o.id, o.business_id, b.name AS business_name,
                o.title, o.description, o.status,
                o.department, o.budget, o.created_at
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE o.id = ?
            """,
            (opportunity_id,)
        ).fetchone()

    if not row:
        raise ValueError("Opportunity not found")

    return dict(row)
