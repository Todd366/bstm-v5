"""What staff need to act on right now."""

from app.db.database import transaction


def review_queue():
    with transaction() as db:
        applications = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.created_at, y.id AS youth_id,
                   y.name AS youth_name, y.location AS youth_location, y.level,
                   o.id AS opportunity_id, o.title AS opportunity_title,
                   o.budget, b.name AS business_name
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE oa.status = 'Pending'
            ORDER BY oa.created_at ASC LIMIT 100
            """
        ).fetchall()

        trials = db.execute(
            """
            SELECT t.id AS trial_id, t.status, t.submission, t.submitted_at,
                   t.assignment_id, y.name AS youth_name,
                   o.title AS opportunity_title, b.name AS business_name
            FROM trials t
            JOIN opportunity_assignments oa ON oa.id = t.assignment_id
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE t.status IN ('Submitted', 'Under Review')
            ORDER BY t.submitted_at ASC LIMIT 100
            """
        ).fetchall()

    return {
        "applications": [dict(r) for r in applications],
        "trials": [dict(r) for r in trials],
    }
