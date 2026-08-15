import json

import psycopg2.extras

from app.db.database import transaction
from app.services.progression_service import (
    apply_progression,
    capability_gain_for_review,
    RELIABILITY_GAIN_ON_COMPLETE,
    RELIABILITY_LOSS_ON_CANCEL,
)


def create_trial(assignment_id, title=None, description=None):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT id, youth_id, opportunity_id, status
            FROM opportunity_assignments
            WHERE id = ?
            """,
            (assignment_id,),
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] != "Accepted":
            raise ValueError("Only accepted assignments can create trials")

        existing = db.execute(
            "SELECT id FROM trials WHERE assignment_id = ?",
            (assignment_id,),
        ).fetchone()

        if existing:
            raise ValueError("Trial already exists for this assignment")

        opportunity = db.execute(
            "SELECT title, description FROM opportunities WHERE id = ?",
            (assignment["opportunity_id"],),
        ).fetchone()

        trial_title = title if title else opportunity["title"]
        trial_description = (
            description if description is not None else opportunity["description"]
        )

        row = db.execute(
            """
            INSERT INTO trials (
                assignment_id, title, description, status
            )
            VALUES (?, ?, ?, 'Created')
            RETURNING id
            """,
            (assignment_id, trial_title, trial_description),
        ).fetchone()

        trial_id = row["id"]

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "trial_created",
                assignment["youth_id"],
                trial_id,
                json.dumps(
                    {
                        "trial_id": str(trial_id),
                        "assignment_id": str(assignment["id"]),
                        "youth_id": str(assignment["youth_id"]),
                        "opportunity_id": str(assignment["opportunity_id"]),
                        "status": "Created",
                    }
                ),
            ),
        )

    return str(trial_id)


def _get_trial_with_assignment(db, trial_id):
    """Not in the original — the original trials table stored youth_id and
    opportunity_id directly on the row; this schema derives them via the
    assignment instead, so every status-transition function needs this join
    rather than a plain SELECT * FROM trials WHERE id = ?."""

    return db.execute(
        """
        SELECT
            t.id, t.status, t.assignment_id,
            oa.youth_id, oa.opportunity_id
        FROM trials t
        JOIN opportunity_assignments oa ON oa.id = t.assignment_id
        WHERE t.id = ?
        """,
        (trial_id,),
    ).fetchone()


def start_trial(trial_id):

    if not trial_id:
        raise ValueError("Trial ID is required")

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id)

        if not trial:
            raise ValueError("Trial not found")

        if trial["status"] != "Created":
            raise ValueError("Only created trials can be started")

        db.execute(
            "UPDATE trials SET status = 'Active', started_at = now() WHERE id = ?",
            (trial_id,),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "trial_started",
                trial["youth_id"],
                trial_id,
                json.dumps(
                    {
                        "trial_id": str(trial_id),
                        "assignment_id": str(trial["assignment_id"]),
                        "youth_id": str(trial["youth_id"]),
                        "opportunity_id": str(trial["opportunity_id"]),
                        "status": "Active",
                    }
                ),
            ),
        )

    return str(trial_id)


def submit_trial(trial_id, submission=None):

    if not trial_id:
        raise ValueError("Trial ID is required")

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id)

        if not trial:
            raise ValueError("Trial not found")

        if trial["status"] != "Active":
            raise ValueError("Only active trials can be submitted")

        # submission is jsonb — wrap non-null values so psycopg2 adapts
        # them correctly.
        submission_param = (
            psycopg2.extras.Json(submission) if submission is not None else None
        )

        db.execute(
            """
            UPDATE trials
            SET status = 'Submitted', submission = ?, submitted_at = now()
            WHERE id = ?
            """,
            (submission_param, trial_id),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "trial_submitted",
                trial["youth_id"],
                trial_id,
                json.dumps(
                    {
                        "trial_id": str(trial_id),
                        "assignment_id": str(trial["assignment_id"]),
                        "youth_id": str(trial["youth_id"]),
                        "opportunity_id": str(trial["opportunity_id"]),
                        "status": "Submitted",
                    }
                ),
            ),
        )

    return str(trial_id)


def review_trial(trial_id, review=None):

    if not trial_id:
        raise ValueError("Trial ID is required")

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id)

        if not trial:
            raise ValueError("Trial not found")

        if trial["status"] != "Submitted":
            raise ValueError("Only submitted trials can be reviewed")

        review_param = psycopg2.extras.Json(review) if review is not None else None

        db.execute(
            """
            UPDATE trials
            SET status = 'Under Review', review = ?, reviewed_at = now()
            WHERE id = ?
            """,
            (review_param, trial_id),
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "trial_review_started",
                trial["youth_id"],
                trial_id,
                json.dumps(
                    {
                        "trial_id": str(trial_id),
                        "assignment_id": str(trial["assignment_id"]),
                        "youth_id": str(trial["youth_id"]),
                        "opportunity_id": str(trial["opportunity_id"]),
                        "status": "Under Review",
                    }
                ),
            ),
        )

    return str(trial_id)


def complete_trial(trial_id, review=None):

    if not trial_id:
        raise ValueError("Trial ID is required")

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id)

        if not trial:
            raise ValueError("Trial not found")

        if trial["status"] != "Under Review":
            raise ValueError("Only trials under review can be completed")

        # The review that actually ends up stored is either the one passed
        # to this call, or (more commonly) the one already recorded by an
        # earlier review_trial() step. The progression gain must be based
        # on that same effective value, not just whatever (if anything)
        # was passed here — otherwise a normal complete() call with no
        # review argument silently discards the real review score.
        existing_review_row = db.execute(
            "SELECT review FROM trials WHERE id = ?",
            (trial_id,),
        ).fetchone()

        effective_review = review if review is not None else existing_review_row["review"]

        review_param = psycopg2.extras.Json(review) if review is not None else None

        db.execute(
            """
            UPDATE trials
            SET status = 'Completed',
                review = COALESCE(?, review),
                completed_at = now()
            WHERE id = ?
            """,
            (review_param, trial_id),
        )

        db.execute(
            "UPDATE youth SET completed_trials = completed_trials + 1 WHERE id = ?",
            (trial["youth_id"],),
        )

        # Progression: a completed trial is real evidence of demonstrated
        # capability. Gain scales with the review's score if the reviewer
        # gave one, otherwise a modest default so completion still counts.
        apply_progression(
            db,
            trial["youth_id"],
            capability_delta=capability_gain_for_review(effective_review),
            reliability_delta=RELIABILITY_GAIN_ON_COMPLETE,
        )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "trial_completed",
                trial["youth_id"],
                trial_id,
                json.dumps(
                    {
                        "trial_id": str(trial_id),
                        "assignment_id": str(trial["assignment_id"]),
                        "youth_id": str(trial["youth_id"]),
                        "opportunity_id": str(trial["opportunity_id"]),
                        "status": "Completed",
                    }
                ),
            ),
        )

    return str(trial_id)


def cancel_trial(trial_id, reason=None):

    if not trial_id:
        raise ValueError("Trial ID is required")

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id)

        if not trial:
            raise ValueError("Trial not found")

        if trial["status"] in ("Completed", "Cancelled"):
            raise ValueError("Completed or cancelled trials cannot be cancelled")

        db.execute(
            """
            UPDATE trials
            SET status = 'Cancelled', cancellation_reason = ?, cancelled_at = now()
            WHERE id = ?
            """,
            (reason, trial_id),
        )

        # Progression: only penalize reliability if the trial had actually
        # been started (Active/Submitted/Under Review). Cancelling
        # something that was created but never begun isn't a reliability
        # failure — nothing was actually abandoned.
        if trial["status"] != "Created":
            apply_progression(
                db,
                trial["youth_id"],
                reliability_delta=-RELIABILITY_LOSS_ON_CANCEL,
            )

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "trial_cancelled",
                trial["youth_id"],
                trial_id,
                json.dumps(
                    {
                        "trial_id": str(trial_id),
                        "assignment_id": str(trial["assignment_id"]),
                        "youth_id": str(trial["youth_id"]),
                        "opportunity_id": str(trial["opportunity_id"]),
                        "status": "Cancelled",
                        "reason": reason,
                    }
                ),
            ),
        )

    return str(trial_id)


def get_trial(trial_id):

    if not trial_id:
        raise ValueError("Trial ID is required")

    with transaction() as db:

        row = db.execute(
            """
            SELECT
                t.id AS trial_id,
                t.assignment_id,
                oa.opportunity_id,
                o.title AS opportunity_title,
                o.description AS opportunity_description,
                oa.youth_id,
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
            JOIN opportunity_assignments oa ON oa.id = t.assignment_id
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE t.id = ?
            """,
            (trial_id,),
        ).fetchone()

    if not row:
        raise ValueError("Trial not found")

    return dict(row)


def list_youth_trials(youth_id):

    if not youth_id:
        raise ValueError("Youth ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                t.id AS trial_id,
                t.assignment_id,
                oa.opportunity_id,
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
            JOIN opportunity_assignments oa ON oa.id = t.assignment_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.youth_id = ?
            ORDER BY t.created_at DESC
            """,
            (youth_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_assignment_trials(assignment_id):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                t.id AS trial_id,
                t.assignment_id,
                oa.opportunity_id,
                oa.youth_id,
                t.title,
                t.description,
                t.status,
                t.created_at,
                t.started_at,
                t.submitted_at,
                t.reviewed_at,
                t.completed_at
            FROM trials t
            JOIN opportunity_assignments oa ON oa.id = t.assignment_id
            WHERE t.assignment_id = ?
            ORDER BY t.created_at DESC
            """,
            (assignment_id,),
        ).fetchall()

    return [dict(row) for row in rows]
