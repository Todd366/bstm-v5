import json

from app.core.ids import generate_id
from app.core.time import utc_now

from app.db.database import (
    get_connection,
    transaction
)

def create_trial(
    assignment_id,
    title=None,
    description=None
):

    if not assignment_id:
        raise ValueError(
            "Assignment ID is required"
        )

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT
                id,
                youth_id,
                opportunity_id,
                status
            FROM opportunity_assignments
            WHERE id = ?
            """,
            (
                assignment_id,
            )
        ).fetchone()

        if not assignment:

            raise ValueError(
                "Assignment not found"
            )

        if assignment["status"] != "Accepted":

            raise ValueError(
                "Only accepted assignments can create trials"
            )

        existing = db.execute(
            """
            SELECT id
            FROM trials
            WHERE assignment_id = ?
            """,
            (
                assignment_id,
            )
        ).fetchone()

        if existing:

            raise ValueError(
                "Trial already exists for this assignment"
            )

        opportunity = db.execute(
            """
            SELECT
                title,
                description
            FROM opportunities
            WHERE id = ?
            """,
            (
                assignment["opportunity_id"],
            )
        ).fetchone()

        trial_id = generate_id(
            "TRIAL"
        )

        created_at = utc_now()

        trial_title = (
            title
            if title
            else opportunity["title"]
        )

        trial_description = (
            description
            if description is not None
            else opportunity["description"]
        )

        db.execute(
            """
            INSERT INTO trials (
                id,
                assignment_id,
                opportunity_id,
                youth_id,
                title,
                description,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trial_id,
                assignment["id"],
                assignment["opportunity_id"],
                assignment["youth_id"],
                trial_title,
                trial_description,
                "Created",
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
                "trial_created",
                assignment["youth_id"],
                trial_id,
                json.dumps({
                    "trial_id": trial_id,
                    "assignment_id": assignment["id"],
                    "youth_id": assignment["youth_id"],
                    "opportunity_id": assignment["opportunity_id"],
                    "status": "Created"
                }),
                created_at
            )
        )

    return trial_id


def start_trial(
    trial_id
):

    if not trial_id:
        raise ValueError(
            "Trial ID is required"
        )

    with transaction() as db:

        trial = db.execute(
            """
            SELECT
                id,
                youth_id,
                assignment_id,
                opportunity_id,
                status
            FROM trials
            WHERE id = ?
            """,
            (
                trial_id,
            )
        ).fetchone()

        if not trial:

            raise ValueError(
                "Trial not found"
            )

        if trial["status"] != "Created":

            raise ValueError(
                "Only created trials can be started"
            )

        started_at = utc_now()

        db.execute(
            """
            UPDATE trials
            SET status = ?,
                started_at = ?
            WHERE id = ?
            """,
            (
                "Active",
                started_at,
                trial_id
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
                "trial_started",
                trial["youth_id"],
                trial_id,
                json.dumps({
                    "trial_id": trial_id,
                    "assignment_id": trial["assignment_id"],
                    "youth_id": trial["youth_id"],
                    "opportunity_id": trial["opportunity_id"],
                    "status": "Active"
                }),
                started_at
            )
        )

    return trial_id


def submit_trial(
    trial_id,
    submission=None
):

    if not trial_id:
        raise ValueError(
            "Trial ID is required"
        )

    with transaction() as db:

        trial = db.execute(
            """
            SELECT
                id,
                youth_id,
                assignment_id,
                opportunity_id,
                status
            FROM trials
            WHERE id = ?
            """,
            (
                trial_id,
            )
        ).fetchone()

        if not trial:

            raise ValueError(
                "Trial not found"
            )

        if trial["status"] != "Active":

            raise ValueError(
                "Only active trials can be submitted"
            )

        submitted_at = utc_now()

        db.execute(
            """
            UPDATE trials
            SET status = ?,
                submission = ?,
                submitted_at = ?
            WHERE id = ?
            """,
            (
                "Submitted",
                submission,
                submitted_at,
                trial_id
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
                "trial_submitted",
                trial["youth_id"],
                trial_id,
                json.dumps({
                    "trial_id": trial_id,
                    "assignment_id": trial["assignment_id"],
                    "youth_id": trial["youth_id"],
                    "opportunity_id": trial["opportunity_id"],
                    "status": "Submitted"
                }),
                submitted_at
            )
        )

    return trial_id


def review_trial(
    trial_id,
    review=None
):

    if not trial_id:
        raise ValueError(
            "Trial ID is required"
        )

    with transaction() as db:

        trial = db.execute(
            """
            SELECT
                id,
                youth_id,
                assignment_id,
                opportunity_id,
                status
            FROM trials
            WHERE id = ?
            """,
            (
                trial_id,
            )
        ).fetchone()

        if not trial:

            raise ValueError(
                "Trial not found"
            )

        if trial["status"] != "Submitted":

            raise ValueError(
                "Only submitted trials can be reviewed"
            )

        reviewed_at = utc_now()

        db.execute(
            """
            UPDATE trials
            SET status = ?,
                review = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (
                "Under Review",
                review,
                reviewed_at,
                trial_id
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
                "trial_review_started",
                trial["youth_id"],
                trial_id,
                json.dumps({
                    "trial_id": trial_id,
                    "assignment_id": trial["assignment_id"],
                    "youth_id": trial["youth_id"],
                    "opportunity_id": trial["opportunity_id"],
                    "status": "Under Review"
                }),
                reviewed_at
            )
        )

    return trial_id


def complete_trial(
    trial_id,
    review=None
):

    if not trial_id:
        raise ValueError(
            "Trial ID is required"
        )

    with transaction() as db:

        trial = db.execute(
            """
            SELECT
                id,
                youth_id,
                assignment_id,
                opportunity_id,
                status
            FROM trials
            WHERE id = ?
            """,
            (
                trial_id,
            )
        ).fetchone()

        if not trial:

            raise ValueError(
                "Trial not found"
            )

        if trial["status"] != "Under Review":

            raise ValueError(
                "Only trials under review can be completed"
            )

        completed_at = utc_now()

        db.execute(
            """
            UPDATE trials
            SET status = ?,
                review = COALESCE(?, review),
                completed_at = ?
            WHERE id = ?
            """,
            (
                "Completed",
                review,
                completed_at,
                trial_id
            )
        )

        db.execute(
            """
            UPDATE youth
            SET completed_trials =
                completed_trials + 1
            WHERE id = ?
            """,
            (
                trial["youth_id"],
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
                "trial_completed",
                trial["youth_id"],
                trial_id,
                json.dumps({
                    "trial_id": trial_id,
                    "assignment_id": trial["assignment_id"],
                    "youth_id": trial["youth_id"],
                    "opportunity_id": trial["opportunity_id"],
                    "status": "Completed"
                }),
                completed_at
            )
        )

    return trial_id


def cancel_trial(
    trial_id,
    reason=None
):

    if not trial_id:
        raise ValueError(
            "Trial ID is required"
        )

    with transaction() as db:

        trial = db.execute(
            """
            SELECT
                id,
                youth_id,
                assignment_id,
                opportunity_id,
                status
            FROM trials
            WHERE id = ?
            """,
            (
                trial_id,
            )
        ).fetchone()

        if not trial:

            raise ValueError(
                "Trial not found"
            )

        if trial["status"] in (
            "Completed",
            "Cancelled"
        ):

            raise ValueError(
                "Completed or cancelled trials cannot be cancelled"
            )

        cancelled_at = utc_now()

        db.execute(
            """
            UPDATE trials
            SET status = ?,
                cancellation_reason = ?,
                cancelled_at = ?
            WHERE id = ?
            """,
            (
                "Cancelled",
                reason,
                cancelled_at,
                trial_id
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
                "trial_cancelled",
                trial["youth_id"],
                trial_id,
                json.dumps({
                    "trial_id": trial_id,
                    "assignment_id": trial["assignment_id"],
                    "youth_id": trial["youth_id"],
                    "opportunity_id": trial["opportunity_id"],
                    "status": "Cancelled",
                    "reason": reason
                }),
                cancelled_at
            )
        )

    return trial_id


def get_trial(
    trial_id
):

    if not trial_id:
        raise ValueError(
            "Trial ID is required"
        )

    with get_connection() as db:

        row = db.execute(
            """
            SELECT
                t.id AS trial_id,
                t.assignment_id,
                t.opportunity_id,
                o.title AS opportunity_title,
                o.description AS opportunity_description,
                t.youth_id,
                y.name AS youth_name,
                t.title,
                t.description,
                t.status,
                t.submission,
                t.review,
                t.created_at,
                t.started_at,
                t.submitted_at,
                t.reviewed_at,
                t.completed_at,
                t.cancelled_at,
                t.cancellation_reason
            FROM trials t
            JOIN youth y
                ON y.id = t.youth_id
            JOIN opportunities o
                ON o.id = t.opportunity_id
            WHERE t.id = ?
            """,
            (
                trial_id,
            )
        ).fetchone()

    if not row:

        raise ValueError(
            "Trial not found"
        )

    return dict(row)


def list_youth_trials(
    youth_id
):

    if not youth_id:
        raise ValueError(
            "Youth ID is required"
        )

    with get_connection() as db:

        rows = db.execute(
            """
            SELECT
                t.id AS trial_id,
                t.assignment_id,
                t.opportunity_id,
                o.title AS opportunity_title,
                t.title,
                t.status,
                t.created_at,
                t.started_at,
                t.submitted_at,
                t.reviewed_at,
                t.completed_at,
                t.cancelled_at
            FROM trials t
            JOIN opportunities o
                ON o.id = t.opportunity_id
            WHERE t.youth_id = ?
            ORDER BY t.created_at DESC
            """,
            (
                youth_id,
            )
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def list_assignment_trials(
    assignment_id
):

    if not assignment_id:
        raise ValueError(
            "Assignment ID is required"
        )

    with get_connection() as db:

        rows = db.execute(
            """
            SELECT
                t.id AS trial_id,
                t.assignment_id,
                t.opportunity_id,
                t.youth_id,
                t.title,
                t.description,
                t.status,
                t.created_at,
                t.started_at,
                t.submitted_at,
                t.reviewed_at,
                t.completed_at,
                t.cancelled_at
            FROM trials t
            WHERE t.assignment_id = ?
            ORDER BY t.created_at DESC
            """,
            (
                assignment_id,
            )
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]
