"""
Opportunity assignments.

Two ways an assignment row is born:

  application  A youth applies. Status 'Pending', the opportunity stays
               'Open' so other youth can apply too. BSTM (admin) later
               accepts exactly one applicant; the rest are declined.
  offer        BSTM assigns a youth directly. The opportunity becomes
               'Assigned' immediately (closed to others); the youth then
               accepts or declines. Other pending applications are
               declined.

Every state change locks the opportunity row first, then the assignment
row, so concurrent requests cannot double-assign an opportunity.

`acting_youth_id` (when given) makes the call a self-service one: the
assignment must belong to that youth, otherwise it reports "not found".
"""

import json

import psycopg2

from app.core.config import MAX_OPEN_APPLICATIONS
from app.core.errors import Conflict, Forbidden
from app.core.validation import require_uuid
from app.db.database import transaction


VALID_STATUSES = [
    "Pending",
    "Accepted",
    "Declined",
    "Cancelled",
    "Completed",
]

YOUTH_REVENUE_SHARE = 0.70


def _log(db, event, actor_id, target_id, details):
    db.execute(
        """
        INSERT INTO activity (event, actor_id, target_id, details)
        VALUES (?, ?, ?, ?)
        """,
        (event, actor_id, target_id, json.dumps(details)),
    )


def _lock_assignment(db, assignment_id, acting_youth_id=None):
    """Locks the opportunity, then the assignment, and returns the
    assignment joined with youth/opportunity facts."""

    assignment_id = require_uuid(assignment_id, "Assignment")

    parent = db.execute(
        "SELECT opportunity_id FROM opportunity_assignments WHERE id = ?",
        (assignment_id,),
    ).fetchone()

    if not parent:
        raise ValueError("Assignment not found")

    db.execute(
        "SELECT id FROM opportunities WHERE id = ? FOR UPDATE",
        (parent["opportunity_id"],),
    )

    row = db.execute(
        """
        SELECT oa.id, oa.youth_id, oa.opportunity_id, oa.status,
               y.name AS youth_name,
               o.title AS opportunity_title,
               o.status AS opportunity_status,
               o.budget
        FROM opportunity_assignments oa
        JOIN youth y ON y.id = oa.youth_id
        JOIN opportunities o ON o.id = oa.opportunity_id
        WHERE oa.id = ?
        FOR UPDATE OF oa
        """,
        (assignment_id,),
    ).fetchone()

    if not row:
        raise ValueError("Assignment not found")

    if acting_youth_id is not None and str(row["youth_id"]) != str(acting_youth_id):
        # Same answer as a missing row: never confirm another person's
        # assignment exists.
        raise ValueError("Assignment not found")

    return row


def _decline_other_pending(db, opportunity_id, keep_assignment_id, reason):
    declined = db.execute(
        """
        UPDATE opportunity_assignments
        SET status = 'Declined'
        WHERE opportunity_id = ? AND id <> ? AND status = 'Pending'
        RETURNING id, youth_id
        """,
        (opportunity_id, keep_assignment_id),
    ).fetchall()

    for other in declined:
        _log(
            db,
            "assignment_declined",
            other["youth_id"],
            other["id"],
            {"reason": reason, "opportunity_id": str(opportunity_id)},
        )


def create_assignment(youth_id, opportunity_id, match_id=None, mode="offer"):

    youth_id = require_uuid(youth_id, "Youth")
    opportunity_id = require_uuid(opportunity_id, "Opportunity")
    match_id = require_uuid(match_id, "Opportunity match") if match_id else None

    if mode not in ("offer", "application"):
        raise ValueError("Invalid assignment mode")

    try:
        with transaction() as db:

            youth = db.execute(
                "SELECT id, name FROM youth WHERE id = ?",
                (youth_id,),
            ).fetchone()

            if not youth:
                raise ValueError("Youth not found")

            opportunity = db.execute(
                """
                SELECT id, business_id, title, description, status
                FROM opportunities
                WHERE id = ?
                FOR UPDATE
                """,
                (opportunity_id,),
            ).fetchone()

            if not opportunity:
                raise ValueError("Opportunity not found")

            existing = db.execute(
                "SELECT id FROM opportunity_assignments WHERE youth_id = ? AND opportunity_id = ?",
                (youth_id, opportunity_id),
            ).fetchone()

            if existing:
                raise Conflict(
                    "You have already applied to this opportunity"
                    if mode == "application"
                    else "Assignment already exists"
                )

            if opportunity["status"] != "Open":
                raise Conflict("Opportunity is not open")

            if match_id:

                match = db.execute(
                    "SELECT id, youth_id, opportunity_id FROM opportunity_matches WHERE id = ?",
                    (match_id,),
                ).fetchone()

                if not match:
                    raise ValueError("Opportunity match not found")

                if str(match["youth_id"]) != youth_id:
                    raise ValueError("Match does not belong to youth")

                if str(match["opportunity_id"]) != opportunity_id:
                    raise ValueError("Match does not belong to opportunity")

            if mode == "application":

                open_applications = db.execute(
                    """
                    SELECT count(*) AS n
                    FROM opportunity_assignments oa
                    JOIN opportunities o ON o.id = oa.opportunity_id
                    WHERE oa.youth_id = ? AND oa.status = 'Pending' AND o.status = 'Open'
                    """,
                    (youth_id,),
                ).fetchone()["n"]

                if open_applications >= MAX_OPEN_APPLICATIONS:
                    raise Conflict(
                        f"You can have at most {MAX_OPEN_APPLICATIONS} open applications. "
                        "Withdraw one or wait for a reply first."
                    )

            row = db.execute(
                """
                INSERT INTO opportunity_assignments (
                    youth_id, opportunity_id, match_id, status
                )
                VALUES (?, ?, ?, 'Pending')
                RETURNING id
                """,
                (youth_id, opportunity_id, match_id),
            ).fetchone()

            assignment_id = row["id"]

            if mode == "offer":

                db.execute(
                    "UPDATE opportunities SET status = 'Assigned', updated_at = now() WHERE id = ?",
                    (opportunity_id,),
                )

                _decline_other_pending(
                    db, opportunity_id, assignment_id, "opportunity offered to someone else"
                )

            _log(
                db,
                "opportunity_assigned" if mode == "offer" else "opportunity_applied",
                youth_id,
                assignment_id,
                {
                    "assignment_id": str(assignment_id),
                    "opportunity_id": opportunity_id,
                    "opportunity_title": opportunity["title"],
                    "match_id": match_id,
                    "status": "Pending",
                    "mode": mode,
                },
            )

    except psycopg2.errors.UniqueViolation:
        raise Conflict("Assignment already exists")

    return str(assignment_id)


def accept_assignment(assignment_id, acting_youth_id=None):

    with transaction() as db:

        assignment = _lock_assignment(db, assignment_id, acting_youth_id)

        if assignment["status"] != "Pending":
            raise ValueError("Only pending assignments can be accepted")

        is_application = assignment["opportunity_status"] == "Open"
        is_offer = assignment["opportunity_status"] == "Assigned"

        if not (is_application or is_offer):
            raise Conflict("This opportunity is no longer available")

        if is_application and acting_youth_id is not None:
            raise Forbidden("Only BSTM can accept an application")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Accepted', accepted_at = now() WHERE id = ?",
            (assignment["id"],),
        )

        db.execute(
            "UPDATE opportunities SET status = 'InProgress', updated_at = now() WHERE id = ?",
            (assignment["opportunity_id"],),
        )

        if is_application:
            _decline_other_pending(
                db,
                assignment["opportunity_id"],
                assignment["id"],
                "another applicant was selected",
            )

        _log(
            db,
            "assignment_accepted",
            assignment["youth_id"],
            assignment["id"],
            {
                "assignment_id": str(assignment["id"]),
                "opportunity_id": str(assignment["opportunity_id"]),
                "opportunity_title": assignment["opportunity_title"],
                "status": "Accepted",
            },
        )

    return str(assignment["id"])


def decline_assignment(assignment_id, acting_youth_id=None):

    with transaction() as db:

        assignment = _lock_assignment(db, assignment_id, acting_youth_id)

        if assignment["status"] != "Pending":
            raise ValueError("Only pending assignments can be declined")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Declined' WHERE id = ?",
            (assignment["id"],),
        )

        # A declined direct offer frees the opportunity again. Declining
        # an application (opportunity still 'Open') changes nothing else.
        if assignment["opportunity_status"] == "Assigned":
            db.execute(
                "UPDATE opportunities SET status = 'Open', updated_at = now() WHERE id = ?",
                (assignment["opportunity_id"],),
            )

        _log(
            db,
            "assignment_declined",
            assignment["youth_id"],
            assignment["id"],
            {
                "assignment_id": str(assignment["id"]),
                "opportunity_id": str(assignment["opportunity_id"]),
                "status": "Declined",
            },
        )

    return str(assignment["id"])


def cancel_assignment(assignment_id, acting_youth_id=None):
    """Withdraws/cancels an assignment. Any unfinished trial under it is
    cancelled too (with the reliability penalty if work had started),
    and the opportunity is reopened if this assignment was holding it."""

    # Imported here: trial_service imports nothing from this module, but
    # keeping the import local makes the dependency direction explicit.
    from app.services.trial_service import cancel_open_trials_in_transaction

    with transaction() as db:

        assignment = _lock_assignment(db, assignment_id, acting_youth_id)

        if assignment["status"] in ("Completed", "Cancelled", "Declined"):
            raise ValueError("Assignment cannot be cancelled")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Cancelled' WHERE id = ?",
            (assignment["id"],),
        )

        cancel_open_trials_in_transaction(
            db, assignment["id"], assignment["youth_id"], "Assignment cancelled"
        )

        if assignment["opportunity_status"] in ("Assigned", "InProgress"):
            db.execute(
                "UPDATE opportunities SET status = 'Open', updated_at = now() WHERE id = ?",
                (assignment["opportunity_id"],),
            )

        _log(
            db,
            "assignment_cancelled",
            assignment["youth_id"],
            assignment["id"],
            {
                "assignment_id": str(assignment["id"]),
                "opportunity_id": str(assignment["opportunity_id"]),
                "status": "Cancelled",
            },
        )

    return str(assignment["id"])


def complete_assignment(assignment_id):

    with transaction() as db:

        assignment = _lock_assignment(db, assignment_id)

        if assignment["status"] != "Accepted":
            raise ValueError("Only accepted assignments can be completed")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Completed', completed_at = now() WHERE id = ?",
            (assignment["id"],),
        )

        db.execute(
            "UPDATE opportunities SET status = 'Completed', updated_at = now() WHERE id = ?",
            (assignment["opportunity_id"],),
        )

        db.execute(
            "UPDATE youth SET completed_opportunities = completed_opportunities + 1 WHERE id = ?",
            (assignment["youth_id"],),
        )

        budget = float(assignment["budget"] or 0)
        youth_share = round(budget * YOUTH_REVENUE_SHARE, 2)
        ecosystem_share = round(budget - youth_share, 2)

        if budget > 0:

            db.execute(
                "UPDATE youth SET revenue = revenue + ? WHERE id = ?",
                (youth_share, assignment["youth_id"]),
            )

            _log(
                db,
                "revenue_distributed",
                assignment["youth_id"],
                assignment["id"],
                {
                    "assignment_id": str(assignment["id"]),
                    "opportunity_id": str(assignment["opportunity_id"]),
                    "budget": budget,
                    "youth_share": youth_share,
                    "ecosystem_share": ecosystem_share,
                },
            )

        _log(
            db,
            "assignment_completed",
            assignment["youth_id"],
            assignment["id"],
            {
                "assignment_id": str(assignment["id"]),
                "opportunity_id": str(assignment["opportunity_id"]),
                "status": "Completed",
            },
        )

    return str(assignment["id"])


def get_assignment(assignment_id, acting_youth_id=None):

    assignment_id = require_uuid(assignment_id, "Assignment")

    with transaction() as db:

        row = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, y.name AS youth_name,
                   oa.opportunity_id, o.title AS opportunity_title,
                   o.description AS opportunity_description,
                   o.status AS opportunity_status, o.business_id,
                   oa.match_id, oa.status, oa.assigned_at, oa.accepted_at,
                   oa.completed_at, oa.created_at
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,),
        ).fetchone()

    if not row:
        raise ValueError("Assignment not found")

    if acting_youth_id is not None and str(row["youth_id"]) != str(acting_youth_id):
        raise ValueError("Assignment not found")

    return dict(row)


def list_youth_assignments(youth_id):
    """A youth's own assignments, with what the UI needs to show the
    next step: the opportunity, its business, and the trial (if any)."""

    youth_id = require_uuid(youth_id, "Youth")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, oa.opportunity_id,
                   o.title AS opportunity_title,
                   o.description AS opportunity_description,
                   o.status AS opportunity_status, o.budget, o.department,
                   o.business_id, b.name AS business_name,
                   b.location AS business_location,
                   oa.match_id, oa.status, oa.assigned_at,
                   oa.accepted_at, oa.completed_at, oa.created_at,
                   t.id AS trial_id, t.status AS trial_status
            FROM opportunity_assignments oa
            JOIN opportunities o ON o.id = oa.opportunity_id
            LEFT JOIN businesses b ON b.id = o.business_id
            LEFT JOIN trials t ON t.assignment_id = oa.id
            WHERE oa.youth_id = ?
            ORDER BY oa.created_at DESC
            """,
            (youth_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_opportunity_assignments(opportunity_id):

    opportunity_id = require_uuid(opportunity_id, "Opportunity")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, y.name AS youth_name,
                   y.level AS youth_level, y.location AS youth_location,
                   oa.opportunity_id, oa.match_id, oa.status, oa.assigned_at,
                   oa.accepted_at, oa.completed_at, oa.created_at
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            WHERE oa.opportunity_id = ?
            ORDER BY oa.created_at DESC
            """,
            (opportunity_id,),
        ).fetchall()

    return [dict(row) for row in rows]
