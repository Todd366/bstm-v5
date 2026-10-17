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

        jobs = db.execute(
            """
            SELECT o.id AS opportunity_id, o.title, o.description, o.department, o.budget,
                   o.created_at, b.name AS business_name, b.location AS business_location
            FROM opportunities o JOIN businesses b ON b.id = o.business_id
            WHERE o.approval_status = 'Pending'
            ORDER BY o.created_at ASC LIMIT 100
            """
        ).fetchall()

        payments = db.execute(
            """
            SELECT p.id AS payment_id, p.amount, p.method, p.provider_ref, p.note, p.created_at,
                   i.reference AS invoice_reference, b.name AS business_name
            FROM payments p
            JOIN invoices i ON i.id = p.invoice_id
            JOIN businesses b ON b.id = i.business_id
            WHERE p.status = 'Submitted'
            ORDER BY p.created_at ASC LIMIT 100
            """
        ).fetchall()

        payouts = db.execute(
            """
            SELECT po.id AS payout_id, po.amount, po.method, po.destination, po.created_at,
                   y.name AS youth_name, i.reference AS invoice_reference
            FROM payouts po
            JOIN youth y ON y.id = po.youth_id
            JOIN invoices i ON i.id = po.invoice_id
            WHERE po.status = 'Pending'
            ORDER BY po.created_at ASC LIMIT 100
            """
        ).fetchall()

        unmatched = db.execute(
            """
            SELECT id, provider, provider_ref, invoice_reference, amount, reason, created_at
            FROM unmatched_payments WHERE status = 'Open' ORDER BY created_at ASC LIMIT 100
            """
        ).fetchall()

    return {
        "unmatched": [dict(r) for r in unmatched],
        "applications": [dict(r) for r in applications],
        "trials": [dict(r) for r in trials],
        "jobs": [dict(r) for r in jobs],
        "payments": [dict(r) for r in payments],
        "payouts": [dict(r) for r in payouts],
    }


def recent_activity(limit=50):
    limit = max(1, min(int(limit), 200))

    with transaction() as db:
        rows = db.execute(
            "SELECT id, event, actor_id, target_id, details, created_at FROM activity ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [dict(r) for r in rows]
