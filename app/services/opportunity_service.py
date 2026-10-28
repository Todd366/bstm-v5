import json

from app.core.departments import DEPARTMENTS
from app.core.validation import clean_text, require_uuid
from app.db.database import transaction


ALLOWED_STATUSES = (
    "Open",
    "Matched",
    "Assigned",
    "InProgress",
    "Completed",
    "Cancelled",
)

MAX_BUDGET = 10_000_000

_OPPORTUNITY_COLUMNS = """
    o.id, o.business_id, b.name AS business_name,
    b.location AS business_location,
    o.title, o.description, o.status,
    o.department, o.budget, o.created_at, o.approval_status, o.created_by
"""


def create_opportunity(
    business_id,
    title,
    description=None,
    department=None,
    budget=0,
    approval_status="Approved",
    created_by="staff",
):

    business_id = require_uuid(business_id, "Business")
    title = clean_text(title, "Opportunity title", 200)
    description = clean_text(description, "Description", 4000, required=False)
    department = clean_text(department, "Department", 100, required=False)

    if department is not None and department not in DEPARTMENTS:
        raise ValueError("Invalid department")

    if budget is None:
        budget = 0

    try:
        budget = float(budget)
    except (TypeError, ValueError):
        raise ValueError("Budget must be a number")

    if budget < 0:
        raise ValueError("Budget cannot be negative")

    if budget > MAX_BUDGET:
        raise ValueError("Budget is too large")

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
                status, department, budget, approval_status, created_by
            )
            VALUES (?, ?, ?, 'Open', ?, ?, ?, ?)
            RETURNING id
            """,
            (business_id, title, description, department, budget, approval_status, created_by),
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
                        "business_name": business["name"],
                        "title": title,
                        "department": department,
                        "budget": budget,
                    }
                ),
            ),
        )

    return str(opportunity_id)


def list_opportunities(limit=100, offset=0, status=None, approval=None):

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    if status is not None and status not in ALLOWED_STATUSES:
        raise ValueError("Invalid opportunity status")

    if approval is not None and approval not in ("Pending", "Approved", "Rejected"):
        raise ValueError("Invalid approval status")

    with transaction() as db:

        rows = db.execute(
            f"""
            SELECT {_OPPORTUNITY_COLUMNS}
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE (?::text IS NULL OR o.status = ?)
              AND (?::text IS NULL OR o.approval_status = ?)
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (status, status, approval, approval, limit, offset),
        ).fetchall()

    return [dict(row) for row in rows]


def browse_open_opportunities(youth_id, limit=50, offset=0, q=None, location=None, department=None):
    """All open opportunities the youth has not applied to yet — for
    youth with few or no claimed skills, where matching returns little."""

    youth_id = require_uuid(youth_id, "Youth")
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    q = clean_text(q, "Search", 80, required=False)
    location = clean_text(location, "Location", 120, required=False)
    department = clean_text(department, "Department", 100, required=False)
    like = "%" + q.replace("%", "").replace("_", "") + "%" if q else None
    place = "%" + location.replace("%", "").replace("_", "") + "%" if location else None

    with transaction() as db:

        rows = db.execute(
            f"""
            SELECT {_OPPORTUNITY_COLUMNS}
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE o.status = 'Open' AND o.approval_status = 'Approved'
              AND NOT EXISTS (
                  SELECT 1 FROM opportunity_assignments oa
                  WHERE oa.opportunity_id = o.id AND oa.youth_id = ?
              )
              AND (?::text IS NULL OR o.title ILIKE ? OR o.description ILIKE ?)
              AND (?::text IS NULL OR b.location ILIKE ?)
              AND (?::text IS NULL OR o.department = ?)
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (youth_id, like, like, like, place, place, department, department, limit, offset),
        ).fetchall()

    return [dict(row) for row in rows]


def get_opportunity(opportunity_id):

    opportunity_id = require_uuid(opportunity_id, "Opportunity")

    with transaction() as db:

        row = db.execute(
            f"""
            SELECT {_OPPORTUNITY_COLUMNS}
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE o.id = ?
            """,
            (opportunity_id,),
        ).fetchone()

    if not row:
        raise ValueError("Opportunity not found")

    return dict(row)


def close_opportunity(opportunity_id):
    """Withdraws a job nobody is working on: declines waiting applicants
    and marks it Cancelled. Refused once someone has been accepted."""

    opportunity_id = require_uuid(opportunity_id, "Opportunity")

    with transaction() as db:

        opp = db.execute(
            "SELECT id, status FROM opportunities WHERE id = ? FOR UPDATE",
            (opportunity_id,),
        ).fetchone()

        if not opp:
            raise ValueError("Opportunity not found")

        if opp["status"] != "Open":
            raise ValueError("Only open jobs can be closed. Cancel the active assignment first.")

        busy = db.execute(
            """
            SELECT 1 FROM opportunity_assignments
            WHERE opportunity_id = ? AND status = 'Accepted'
            """,
            (opportunity_id,),
        ).fetchone()

        if busy:
            raise ValueError("Someone is already working on this job.")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Declined' WHERE opportunity_id = ? AND status = 'Pending'",
            (opportunity_id,),
        )
        db.execute(
            "UPDATE opportunities SET status = 'Cancelled', updated_at = now() WHERE id = ?",
            (opportunity_id,),
        )
        db.execute(
            "INSERT INTO activity (event, actor_id, target_id, details) VALUES (?, NULL, ?, ?)",
            ("opportunity_closed", opportunity_id, "{}"),
        )

    return {"id": opportunity_id, "status": "Cancelled"}


def set_opportunity_approval(opportunity_id, approved, note=None, decided_by=None):
    """Staff decision on a job a business posted. Approved jobs become
    visible to youth; rejected ones are closed. Notifies the business."""

    from app.services.notification_service import notify

    opportunity_id = require_uuid(opportunity_id, "Opportunity")
    note = clean_text(note, "Reason", 300, required=False)
    new_status = "Approved" if approved else "Rejected"

    with transaction() as db:

        opp = db.execute(
            "SELECT id, title, business_id, approval_status FROM opportunities WHERE id = ? FOR UPDATE",
            (opportunity_id,),
        ).fetchone()

        if not opp:
            raise ValueError("Opportunity not found")

        if opp["approval_status"] != "Pending":
            raise ValueError("This job has already been reviewed")

        if approved:
            db.execute(
                "UPDATE opportunities SET approval_status = 'Approved', updated_at = now() WHERE id = ?",
                (opportunity_id,),
            )
        else:
            db.execute(
                "UPDATE opportunities SET approval_status = 'Rejected', status = 'Cancelled', updated_at = now() WHERE id = ?",
                (opportunity_id,),
            )

        db.execute(
            "INSERT INTO activity (event, actor_id, target_id, details) VALUES (?, ?, ?, ?)",
            ("opportunity_" + new_status.lower(), opp["business_id"], opportunity_id, json.dumps({"reason": note, "by": decided_by})),
        )

        notify(
            db, "business", opp["business_id"], "job_" + new_status.lower(),
            "Your job was " + new_status.lower(),
            ('"' + opp["title"] + '" is now live for youth to apply.') if approved
            else ('"' + opp["title"] + '" was not approved.' + ((" Reason: " + note) if note else "")),
        )

    return {"id": opportunity_id, "approval_status": new_status}
