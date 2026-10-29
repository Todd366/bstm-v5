"""The app watching itself: finds things that are stuck, wrong or waiting,
and says what to do. Every item is measured from live data.

area: money | field | team | data  (each staff role sees its own areas)
level: fail (something is wrong), warn (waiting too long), info
"""

from app.db.database import transaction

AREAS_BY_ROLE = {
    "owner": {"money", "field", "team", "data"},
    "admin": {"money", "field", "data"},
    "finance": {"money"},
    "field": {"field", "data"},
    "support": {"data"},
}


def _item(level, area, title, detail, tab):
    return {"level": level, "area": area, "title": title, "detail": detail, "tab": tab}


def _n(db, sql):
    return db.execute(sql).fetchone()["n"]


def collect():
    items = []

    with transaction() as db:
        # ---- facts that must always hold (a failure means a bug or tampering)
        n = _n(db, """
            SELECT count(*) AS n FROM opportunities o
            WHERE o.status = 'Completed' AND o.budget > 0
              AND EXISTS (SELECT 1 FROM opportunity_assignments a WHERE a.opportunity_id = o.id AND a.status = 'Completed')
              AND NOT EXISTS (SELECT 1 FROM invoices i WHERE i.opportunity_id = o.id AND i.status <> 'Void')
              AND NOT EXISTS (SELECT 1 FROM invoices i WHERE i.opportunity_id = o.id)
        """)
        if n:
            items.append(_item("fail", "money", "Paid job finished without an invoice", "%d job(s). Money may be missing." % n, "money"))

        n = _n(db, "SELECT count(*) AS n FROM invoices WHERE status <> 'Void' AND abs(youth_share + platform_share - amount) > 0.01")
        if n:
            items.append(_item("fail", "money", "Invoice split does not add up", "%d invoice(s)." % n, "money"))

        n = _n(db, """
            SELECT count(*) AS n FROM invoices i WHERE i.status <> 'Void'
              AND (SELECT COALESCE(sum(amount), 0) FROM payments p WHERE p.invoice_id = i.id AND p.status = 'Confirmed') > i.amount
        """)
        if n:
            items.append(_item("fail", "money", "Invoice paid more than it is worth", "%d invoice(s)." % n, "money"))

        n = _n(db, """
            SELECT count(*) AS n FROM payouts po JOIN invoices i ON i.id = po.invoice_id
            WHERE po.status <> 'Failed' AND i.status <> 'Paid'
        """)
        if n:
            items.append(_item("fail", "money", "Payout exists for an unpaid invoice", "%d payout(s)." % n, "money"))

        # ---- things waiting on a person
        n = _n(db, "SELECT count(*) AS n FROM payments WHERE status = 'Submitted'")
        if n:
            old = _n(db, "SELECT count(*) AS n FROM payments WHERE status = 'Submitted' AND created_at < now() - interval '2 days'")
            items.append(_item("warn" if old else "info", "money", "Payments to confirm", "%d waiting%s." % (n, (", %d for over 2 days" % old) if old else ""), "queue"))

        n = _n(db, "SELECT count(*) AS n FROM payouts WHERE status = 'Pending'")
        if n:
            old = _n(db, "SELECT count(*) AS n FROM payouts WHERE status = 'Pending' AND created_at < now() - interval '3 days'")
            items.append(_item("warn" if old else "info", "money", "Youth payouts to send", "%d waiting%s. Young people are waiting for their money." % (n, (", %d for over 3 days" % old) if old else ""), "queue"))

        n = _n(db, "SELECT count(*) AS n FROM unmatched_payments WHERE status = 'Open'")
        if n:
            items.append(_item("warn", "money", "Money received that matches no invoice", "%d to resolve." % n, "queue"))

        n = _n(db, "SELECT count(*) AS n FROM invoices WHERE status = 'Issued' AND created_at < now() - interval '14 days'")
        if n:
            items.append(_item("warn", "money", "Invoices unpaid for over 14 days", "%d. Call the business." % n, "money"))

        n = _n(db, "SELECT count(*) AS n FROM opportunity_assignments WHERE status = 'Pending'")
        if n:
            old = _n(db, "SELECT count(*) AS n FROM opportunity_assignments WHERE status = 'Pending' AND created_at < now() - interval '3 days'")
            items.append(_item("warn" if old else "info", "field", "Applications waiting", "%d%s." % (n, (", %d for over 3 days" % old) if old else ""), "queue"))

        n = _n(db, """
            SELECT count(*) AS n FROM trials t WHERE t.status IN ('Submitted', 'Under Review')
              AND COALESCE(t.submitted_at, t.created_at) < now() - interval '3 days'
        """)
        if n:
            items.append(_item("warn", "field", "Work waiting for review over 3 days", "%d. The young person is waiting." % n, "queue"))

        n = _n(db, """
            SELECT count(*) AS n FROM opportunity_assignments a
            WHERE a.status = 'Accepted' AND a.accepted_at < now() - interval '7 days'
              AND NOT EXISTS (SELECT 1 FROM trials t WHERE t.assignment_id = a.id AND t.status <> 'Cancelled')
        """)
        if n:
            items.append(_item("warn", "field", "Accepted but work never started (7+ days)", "%d. Check in with them or free the job." % n, "jobs"))

        n = _n(db, """
            SELECT count(*) AS n FROM opportunities o
            WHERE o.status = 'Open' AND o.approval_status = 'Approved' AND o.created_at < now() - interval '14 days'
              AND NOT EXISTS (SELECT 1 FROM opportunity_assignments a WHERE a.opportunity_id = o.id)
        """)
        if n:
            items.append(_item("info", "field", "Open jobs nobody has touched for 14 days", "%d. Suggest youth or close them." % n, "jobs"))

        n = _n(db, "SELECT count(*) AS n FROM opportunities WHERE approval_status = 'Pending'")
        if n:
            items.append(_item("warn", "field", "Jobs waiting for your approval", "%d. Businesses are waiting." % n, "queue"))

        # ---- people and data quality
        n = _n(db, "SELECT count(*) AS n FROM youth WHERE deleted_at IS NULL AND password_hash IS NULL")
        if n:
            items.append(_item("info", "data", "People who cannot log in", "%d old record(s) with no email or password. Fix or remove them." % n, "owner"))

        n = _n(db, "SELECT count(*) AS n FROM youth WHERE deleted_at IS NULL AND (name ~* '\\m(test|demo|dummy|fake)\\M' OR email ~* '@example\\.')")
        if n:
            items.append(_item("info", "data", "Records that look like tests", "%d. Review in the Owner tab." % n, "owner"))

        try:
            n = _n(db, "SELECT count(*) AS n FROM staff WHERE approved = false")
            if n:
                items.append(_item("warn", "team", "Staff accounts waiting for approval", "%d." % n, "team"))
        except Exception:  # noqa: BLE001 - table not updated yet
            pass

    order = {"fail": 0, "warn": 1, "info": 2}
    items.sort(key=lambda i: order[i["level"]])
    return items


def attention_for(role):
    areas = AREAS_BY_ROLE.get(role, {"data"})
    items = [i for i in collect() if i["area"] in areas]
    return {"items": items, "all_clear": not [i for i in items if i["level"] != "info"]}
