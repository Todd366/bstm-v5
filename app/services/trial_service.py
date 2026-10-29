"""
Trials: the proof-of-work unit inside an accepted assignment.

Lifecycle: Created -> Active -> Submitted -> Under Review -> Completed,
with Cancelled possible before Completed.

`acting_youth_id` (when given) makes a call self-service: the trial must
belong to that youth, otherwise it reports "not found".
"""

import json

import psycopg2.extras

from app.core.errors import Conflict
from app.core.validation import check_json_size, clean_text, require_uuid
from app.db.database import transaction
from app.services.notification_service import notify
from app.services.progression_service import (
    apply_progression,
    capability_gain_for_review,
    RELIABILITY_GAIN_ON_COMPLETE,
    RELIABILITY_LOSS_ON_CANCEL,
)


def _log(db, event, trial, status, extra=None):
    details = {
        "trial_id": str(trial["id"]),
        "assignment_id": str(trial["assignment_id"]),
        "youth_id": str(trial["youth_id"]),
        "opportunity_id": str(trial["opportunity_id"]),
        "status": status,
    }
    if extra:
        details.update(extra)

    db.execute(
        """
        INSERT INTO activity (event, actor_id, target_id, details)
        VALUES (?, ?, ?, ?)
        """,
        (event, trial["youth_id"], trial["id"], json.dumps(details)),
    )


def _get_trial_with_assignment(db, trial_id, acting_youth_id=None):
    """Locks the trial row and returns it with its assignment's
    youth/opportunity. The original schema stored youth_id on the trial;
    this one derives it through the assignment."""

    trial_id = require_uuid(trial_id, "Trial")

    row = db.execute(
        """
        SELECT
            t.id, t.status, t.assignment_id,
            oa.youth_id, oa.opportunity_id
        FROM trials t
        JOIN opportunity_assignments oa ON oa.id = t.assignment_id
        WHERE t.id = ?
        FOR UPDATE OF t
        """,
        (trial_id,),
    ).fetchone()

    if not row:
        raise ValueError("Trial not found")

    if acting_youth_id is not None and str(row["youth_id"]) != str(acting_youth_id):
        raise ValueError("Trial not found")

    return row


def create_trial(assignment_id, title=None, description=None, acting_youth_id=None):

    assignment_id = require_uuid(assignment_id, "Assignment")
    title = clean_text(title, "Title", 200, required=False)
    description = clean_text(description, "Description", 2000, required=False)

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT id, youth_id, opportunity_id, status
            FROM opportunity_assignments
            WHERE id = ?
            FOR UPDATE
            """,
            (assignment_id,),
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if acting_youth_id is not None and str(assignment["youth_id"]) != str(acting_youth_id):
            raise ValueError("Assignment not found")

        if assignment["status"] != "Accepted":
            raise ValueError("Only accepted assignments can create trials")

        existing = db.execute(
            "SELECT id FROM trials WHERE assignment_id = ? AND status <> 'Cancelled'",
            (assignment_id,),
        ).fetchone()

        if existing:
            raise Conflict("Trial already exists for this assignment")

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

        trial = {
            "id": row["id"],
            "assignment_id": assignment["id"],
            "youth_id": assignment["youth_id"],
            "opportunity_id": assignment["opportunity_id"],
        }

        _log(db, "trial_created", trial, "Created")

    return str(trial["id"])


def start_trial(trial_id, acting_youth_id=None):

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id, acting_youth_id)

        if trial["status"] != "Created":
            raise ValueError("Only created trials can be started")

        db.execute(
            "UPDATE trials SET status = 'Active', started_at = now() WHERE id = ?",
            (trial["id"],),
        )

        _log(db, "trial_started", trial, "Active")

    return str(trial["id"])


def submit_trial(trial_id, submission=None, acting_youth_id=None):

    check_json_size(submission, "Submission")

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id, acting_youth_id)

        if trial["status"] != "Active":
            raise ValueError("Only active trials can be submitted")

        submission_param = (
            psycopg2.extras.Json(submission) if submission is not None else None
        )

        db.execute(
            """
            UPDATE trials
            SET status = 'Submitted', submission = ?, submitted_at = now()
            WHERE id = ?
            """,
            (submission_param, trial["id"]),
        )

        _log(db, "trial_submitted", trial, "Submitted")

    return str(trial["id"])


def review_trial(trial_id, review=None):

    check_json_size(review, "Review")

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id)

        if trial["status"] != "Submitted":
            raise ValueError("Only submitted trials can be reviewed")

        review_param = psycopg2.extras.Json(review) if review is not None else None

        db.execute(
            """
            UPDATE trials
            SET status = 'Under Review', review = ?, reviewed_at = now()
            WHERE id = ?
            """,
            (review_param, trial["id"]),
        )

        _log(db, "trial_review_started", trial, "Under Review")

    return str(trial["id"])


def complete_trial(trial_id, review=None):
    """Approves the work. Also finishes the job and issues the invoice in
    the same transaction, so approved work can never sit un-invoiced."""

    from app.services.assignment_service import complete_assignment_in_tx

    check_json_size(review, "Review")

    with transaction() as db:

        # Same lock order as assignment changes: opportunity first.
        parent = db.execute(
            """
            SELECT oa.opportunity_id FROM trials t
            JOIN opportunity_assignments oa ON oa.id = t.assignment_id
            WHERE t.id = ?
            """,
            (require_uuid(trial_id, "Trial"),),
        ).fetchone()

        if parent:
            db.execute("SELECT id FROM opportunities WHERE id = ? FOR UPDATE", (parent["opportunity_id"],))

        trial = _get_trial_with_assignment(db, trial_id)

        if trial["status"] != "Under Review":
            raise ValueError("Only trials under review can be completed")

        # The progression gain must use the review that actually ends up
        # stored: the one passed now, or the one recorded earlier by
        # review_trial().
        existing_review_row = db.execute(
            "SELECT review FROM trials WHERE id = ?",
            (trial["id"],),
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
            (review_param, trial["id"]),
        )

        db.execute(
            "UPDATE youth SET completed_trials = completed_trials + 1 WHERE id = ?",
            (trial["youth_id"],),
        )

        apply_progression(
            db,
            trial["youth_id"],
            capability_delta=capability_gain_for_review(effective_review),
            reliability_delta=RELIABILITY_GAIN_ON_COMPLETE,
        )

        notify(db, "youth", trial["youth_id"], "trial_completed", "Your work was approved",
               "Well done. Your trial was reviewed and completed.")

        _log(db, "trial_completed", trial, "Completed")

        complete_assignment_in_tx(db, trial["assignment_id"])

    return str(trial["id"])


def _cancel_in_transaction(db, trial, reason):
    db.execute(
        """
        UPDATE trials
        SET status = 'Cancelled', cancellation_reason = ?, cancelled_at = now()
        WHERE id = ?
        """,
        (reason, trial["id"]),
    )

    # Only penalise reliability if work had actually started: cancelling
    # something created but never begun abandons nothing.
    if trial["status"] != "Created":
        apply_progression(
            db,
            trial["youth_id"],
            reliability_delta=-RELIABILITY_LOSS_ON_CANCEL,
        )

    _log(db, "trial_cancelled", trial, "Cancelled", {"reason": reason})


def cancel_open_trials_in_transaction(db, assignment_id, youth_id, reason):
    """Cancels every unfinished trial of an assignment, inside the
    caller's transaction (used when an assignment is cancelled)."""

    trials = db.execute(
        """
        SELECT t.id, t.status, t.assignment_id,
               oa.youth_id, oa.opportunity_id
        FROM trials t
        JOIN opportunity_assignments oa ON oa.id = t.assignment_id
        WHERE t.assignment_id = ?
          AND t.status NOT IN ('Completed', 'Cancelled')
        FOR UPDATE OF t
        """,
        (assignment_id,),
    ).fetchall()

    for trial in trials:
        _cancel_in_transaction(db, trial, reason)


def cancel_trial(trial_id, reason=None, acting_youth_id=None):

    reason = clean_text(reason, "Reason", 500, required=False)

    with transaction() as db:

        trial = _get_trial_with_assignment(db, trial_id, acting_youth_id)

        if trial["status"] in ("Completed", "Cancelled"):
            raise ValueError("Completed or cancelled trials cannot be cancelled")

        _cancel_in_transaction(db, trial, reason)

    return str(trial["id"])


def get_trial(trial_id, acting_youth_id=None):

    trial_id = require_uuid(trial_id, "Trial")

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

    if acting_youth_id is not None and str(row["youth_id"]) != str(acting_youth_id):
        raise ValueError("Trial not found")

    return dict(row)


def list_youth_trials(youth_id):

    youth_id = require_uuid(youth_id, "Youth")

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
                t.submission,
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

    assignment_id = require_uuid(assignment_id, "Assignment")

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
