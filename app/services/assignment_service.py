import json

from app.db.database import transaction


VALID_STATUSES = [
    "Pending",
    "Accepted",
    "Declined",
    "Cancelled",
    "Completed",
]

YOUTH_REVENUE_SHARE = 0.70


def create_assignment(youth_id, opportunity_id, match_id=None):

    if not youth_id:
        raise ValueError("Youth ID is required")

    if not opportunity_id:
        raise ValueError("Opportunity ID is required")

    with transaction() as db:

        youth = db.execute(
            "SELECT id, name FROM youth WHERE id = ?",
            (youth_id,),
        ).fetchone()

        if not youth:
            raise ValueError("Youth not found")

        opportunity = db.execute(
            "SELECT id, business_id, title, description, status FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()

        if not opportunity:
            raise ValueError("Opportunity not found")

        if opportunity["status"] != "Open":
            raise ValueError("Opportunity is not open")

        if match_id:

            match = db.execute(
                "SELECT id, youth_id, opportunity_id FROM opportunity_matches WHERE id = ?",
                (match_id,),
            ).fetchone()

            if not match:
                raise ValueError("Opportunity match not found")

            if str(match["youth_id"]) != str(youth_id):
                raise ValueError("Match does not belong to youth")

            if str(match["opportunity_id"]) != str(opportunity_id):
                raise ValueError("Match does not belong to opportunity")

        existing = db.execute(
            "SELECT id, status FROM opportunity_assignments WHERE youth_id = ? AND opportunity_id = ?",
            (youth_id, opportunity_id),
        ).fetchone()

        if existing:
            raise ValueError("Assignment already exists")

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

        # NOTE: not in the original service — closes the opportunity so a
        # second youth can't also be assigned to it while this one is
        # pending/accepted. Reopened on decline/cancel below.
        db.execute(
            "UPDATE opportunities SET status = 'Assigned', updated_at = now() WHERE id = ?",
            (opportunity_id,),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "opportunity_assigned",
                youth_id,
                assignment_id,
                json.dumps(
                    {
                        "assignment_id": str(assignment_id),
                        "youth_id": youth_id,
                        "youth_name": youth["name"],
                        "opportunity_id": opportunity_id,
                        "opportunity_title": opportunity["title"],
                        "match_id": match_id,
                        "status": "Pending",
                    }
                ),
            ),
        )

    return str(assignment_id)


def accept_assignment(assignment_id):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT oa.id, oa.youth_id, oa.opportunity_id, oa.status,
                   y.name AS youth_name, o.title AS opportunity_title
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,),
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] != "Pending":
            raise ValueError("Only pending assignments can be accepted")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Accepted', accepted_at = now() WHERE id = ?",
            (assignment_id,),
        )

        # NOTE: not in the original service — moves the opportunity into
        # InProgress once someone has actually accepted the work.
        db.execute(
            "UPDATE opportunities SET status = 'InProgress', updated_at = now() WHERE id = ?",
            (assignment["opportunity_id"],),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "assignment_accepted",
                assignment["youth_id"],
                assignment_id,
                json.dumps(
                    {
                        "assignment_id": str(assignment_id),
                        "youth_id": str(assignment["youth_id"]),
                        "youth_name": assignment["youth_name"],
                        "opportunity_id": str(assignment["opportunity_id"]),
                        "opportunity_title": assignment["opportunity_title"],
                        "status": "Accepted",
                    }
                ),
            ),
        )

    return str(assignment_id)


def decline_assignment(assignment_id):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT oa.id, oa.youth_id, oa.opportunity_id, oa.status,
                   y.name AS youth_name, o.title AS opportunity_title
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,),
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] != "Pending":
            raise ValueError("Only pending assignments can be declined")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Declined' WHERE id = ?",
            (assignment_id,),
        )

        # NOTE: not in the original service — reopens the opportunity so
        # another youth can be matched/assigned to it.
        db.execute(
            "UPDATE opportunities SET status = 'Open', updated_at = now() WHERE id = ?",
            (assignment["opportunity_id"],),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "assignment_declined",
                assignment["youth_id"],
                assignment_id,
                json.dumps(
                    {
                        "assignment_id": str(assignment_id),
                        "youth_id": str(assignment["youth_id"]),
                        "youth_name": assignment["youth_name"],
                        "opportunity_id": str(assignment["opportunity_id"]),
                        "opportunity_title": assignment["opportunity_title"],
                        "status": "Declined",
                    }
                ),
            ),
        )

    return str(assignment_id)


def cancel_assignment(assignment_id):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            "SELECT id, youth_id, opportunity_id, status FROM opportunity_assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] in ["Completed", "Cancelled", "Declined"]:
            raise ValueError("Assignment cannot be cancelled")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Cancelled' WHERE id = ?",
            (assignment_id,),
        )

        # NOTE: not in the original service — reopens the opportunity,
        # mirroring the decline path above.
        db.execute(
            "UPDATE opportunities SET status = 'Open', updated_at = now() WHERE id = ?",
            (assignment["opportunity_id"],),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "assignment_cancelled",
                assignment["youth_id"],
                assignment_id,
                json.dumps(
                    {
                        "assignment_id": str(assignment_id),
                        "youth_id": str(assignment["youth_id"]),
                        "opportunity_id": str(assignment["opportunity_id"]),
                        "status": "Cancelled",
                    }
                ),
            ),
        )

    return str(assignment_id)


def complete_assignment(assignment_id):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT oa.id, oa.youth_id, oa.opportunity_id, oa.status, o.budget
            FROM opportunity_assignments oa
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,),
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] != "Accepted":
            raise ValueError("Only accepted assignments can be completed")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Completed', completed_at = now() WHERE id = ?",
            (assignment_id,),
        )

        # NOTE: not in the original service.
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

            db.execute(
                """
                INSERT INTO activity (event, actor_id, target_id, details)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "revenue_distributed",
                    assignment["youth_id"],
                    assignment_id,
                    json.dumps(
                        {
                            "assignment_id": str(assignment_id),
                            "youth_id": str(assignment["youth_id"]),
                            "opportunity_id": str(assignment["opportunity_id"]),
                            "budget": budget,
                            "youth_share": youth_share,
                            "ecosystem_share": ecosystem_share,
                        }
                    ),
                ),
            )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "assignment_completed",
                assignment["youth_id"],
                assignment_id,
                json.dumps(
                    {
                        "assignment_id": str(assignment_id),
                        "youth_id": str(assignment["youth_id"]),
                        "opportunity_id": str(assignment["opportunity_id"]),
                        "status": "Completed",
                    }
                ),
            ),
        )

    return str(assignment_id)


def get_assignment(assignment_id):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        row = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, y.name AS youth_name,
                   oa.opportunity_id, o.title AS opportunity_title,
                   o.description AS opportunity_description, o.business_id,
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

    return dict(row)


def list_youth_assignments(youth_id):

    if not youth_id:
        raise ValueError("Youth ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, oa.opportunity_id,
                   o.title AS opportunity_title, o.description AS opportunity_description,
                   o.business_id, oa.match_id, oa.status, oa.assigned_at,
                   oa.accepted_at, oa.completed_at, oa.created_at
            FROM opportunity_assignments oa
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.youth_id = ?
            ORDER BY oa.created_at DESC
            """,
            (youth_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_opportunity_assignments(opportunity_id):

    if not opportunity_id:
        raise ValueError("Opportunity ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, y.name AS youth_name,
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
