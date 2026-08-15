import json

from app.core.departments import DEPARTMENTS
from app.db.database import transaction


ALLOWED_STATUSES = (
    "Open",
    "Matched",
    "Assigned",
    "InProgress",
    "Completed",
    "Cancelled",
)


def create_opportunity(
    business_id,
    title,
    description=None,
    department=None,
    budget=0,
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
            (business_id,),
        ).fetchone()

        if not business:
            raise ValueError("Business not found")

        row = db.execute(
            """
            INSERT INTO opportunities (
                business_id, title, description,
                status, department, budget
            )
            VALUES (?, ?, ?, 'Open', ?, ?)
            RETURNING id
            """,
            (
                business_id,
                title.strip(),
                description.strip() if description else None,
                department,
                budget,
            ),
        ).fetchone()

        opportunity_id = row["id"]

        db.execute(
            """
            UPDATE businesses
            SET opportunities_generated = opportunities_generated + 1,
                updated_at = now()
            WHERE id = ?
            """,
            (business_id,),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "opportunity_created",
                business_id,
                opportunity_id,
                json.dumps(
                    {
                        "business_id": business_id,
                        "business_name": business["name"],
                        "title": title.strip(),
                        "department": department,
                        "budget": budget,
                    }
                ),
            ),
        )

    return str(opportunity_id)


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


def get_opportunity(opportunity_id):

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
            (opportunity_id,),
        ).fetchone()

    if not row:
        raise ValueError("Opportunity not found")

    return dict(row)


def set_opportunity_status(opportunity_id, status):
    """Not in the original service — added because assignment/trial
    workflows need to move an opportunity through its lifecycle
    (Open -> Matched -> Assigned -> InProgress -> Completed/Cancelled),
    and the status column has a CHECK constraint enforcing these values."""

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid opportunity status: {status}")

    with transaction() as db:

        row = db.execute(
            """
            UPDATE opportunities
            SET status = ?, updated_at = now()
            WHERE id = ?
            RETURNING id
            """,
            (status, opportunity_id),
        ).fetchone()

        if not row:
            raise ValueError("Opportunity not found")

    return get_opportunity(opportunity_id)
