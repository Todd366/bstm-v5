import json

import psycopg2

from app.db.database import transaction


# Must match the CHECK constraint on activation.evidence.kind exactly
# (see migrations/20260815000000_baseline_activation_schema.sql).
ALLOWED_KINDS = (
    "Portfolio",
    "Screenshot",
    "Document",
    "BusinessApproval",
    "Assessment",
    "Transaction",
    "Other",
)


def submit_evidence(youth_id, kind, trial_id=None, capability_id=None, url=None, notes=None):
    """Records a piece of evidence for a youth — the concrete artifact
    behind a claim (a portfolio link, a screenshot, a business's
    approval, an assessment result). This is what turns "claimed
    capability" into something demonstrable, per the product's own
    claimed -> demonstrated -> verified distinction.

    trial_id and capability_id are both optional and independent:
    evidence can stand alone (e.g. a general portfolio piece), be tied
    to a specific trial, a specific capability, or both.
    """

    if not youth_id:
        raise ValueError("Youth ID is required")

    if kind not in ALLOWED_KINDS:
        raise ValueError("Invalid evidence kind")

    if not url and not notes:
        raise ValueError("Evidence requires at least a URL or notes")

    with transaction() as db:

        youth = db.execute(
            "SELECT id, name FROM youth WHERE id = ?",
            (youth_id,),
        ).fetchone()

        if not youth:
            raise ValueError("Youth not found")

        if trial_id:

            # A trial's evidence must belong to that same youth — checked
            # via the assignment join, the same pattern trial_service.py
            # uses everywhere else for youth/trial ownership.
            trial = db.execute(
                """
                SELECT t.id, oa.youth_id
                FROM trials t
                JOIN opportunity_assignments oa ON oa.id = t.assignment_id
                WHERE t.id = ?
                """,
                (trial_id,),
            ).fetchone()

            if not trial:
                raise ValueError("Trial not found")

            if str(trial["youth_id"]) != str(youth_id):
                raise ValueError("Trial does not belong to this youth")

        if capability_id:

            capability = db.execute(
                "SELECT id FROM capabilities WHERE id = ?",
                (capability_id,),
            ).fetchone()

            if not capability:
                raise ValueError("Capability not found")

        row = db.execute(
            """
            INSERT INTO evidence (
                youth_id, trial_id, capability_id, kind, url, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                youth_id,
                trial_id,
                capability_id,
                kind,
                url.strip() if url else None,
                notes.strip() if notes else None,
            ),
        ).fetchone()

        evidence_id = row["id"]

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "evidence_submitted",
                youth_id,
                evidence_id,
                json.dumps(
                    {
                        "youth_id": str(youth_id),
                        "youth_name": youth["name"],
                        "kind": kind,
                        "trial_id": str(trial_id) if trial_id else None,
                        "capability_id": str(capability_id) if capability_id else None,
                    }
                ),
            ),
        )

    return str(evidence_id)


def list_youth_evidence(youth_id):

    if not youth_id:
        raise ValueError("Youth ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                e.id, e.youth_id, e.trial_id, e.capability_id,
                c.name AS capability_name,
                e.kind, e.url, e.notes, e.created_at
            FROM evidence e
            LEFT JOIN capabilities c ON c.id = e.capability_id
            WHERE e.youth_id = ?
            ORDER BY e.created_at DESC
            """,
            (youth_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_trial_evidence(trial_id):

    if not trial_id:
        raise ValueError("Trial ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                e.id, e.youth_id, e.trial_id, e.capability_id,
                c.name AS capability_name,
                e.kind, e.url, e.notes, e.created_at
            FROM evidence e
            LEFT JOIN capabilities c ON c.id = e.capability_id
            WHERE e.trial_id = ?
            ORDER BY e.created_at DESC
            """,
            (trial_id,),
        ).fetchall()

    return [dict(row) for row in rows]
