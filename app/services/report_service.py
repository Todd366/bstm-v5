"""Monthly numbers for BSTM, read straight from live records.

Every figure is a count or sum of rows that exist. Nothing is estimated.
Months run on Africa/Gaborone time; money is BWP with 2 decimals."""

import re
from datetime import date

from app.db.database import transaction

TZ = "Africa/Gaborone"


def _bounds(month):
    if month in (None, ""):
        t = date.today()
        month = "%04d-%02d" % (t.year, t.month)
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("Month must look like 2026-10")
    y, m = int(month[:4]), int(month[5:])
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return month, "%04d-%02d-01" % (y, m), "%04d-%02d-01" % (ny, nm)


def monthly_report(month=None):
    month, start, end = _bounds(month)
    # the period in local time, then compared as timestamps
    p = "(%s::date)::timestamp AT TIME ZONE '" + TZ + "'"
    lo, hi = p % "?", p % "?"
    with transaction() as db:
        def n(sql, *extra):
            return db.execute(sql, (start, end) + extra).fetchone()["n"]

        def total(sql):
            return float(db.execute(sql, (start, end)).fetchone()["n"] or 0)

        r = {
            "month": month,
            "people_joined": n("SELECT count(*) AS n FROM youth WHERE deleted_at IS NULL AND created_at >= %s AND created_at < %s" % (lo, hi)),
            "businesses_joined": n("SELECT count(*) AS n FROM businesses WHERE created_at >= %s AND created_at < %s" % (lo, hi)),
            "jobs_posted": n("SELECT count(*) AS n FROM opportunities WHERE created_at >= %s AND created_at < %s" % (lo, hi)),
            "work_submitted": n("SELECT count(*) AS n FROM trials WHERE submitted_at >= %s AND submitted_at < %s" % (lo, hi)),
            "field_cards": n("SELECT count(*) AS n FROM trials WHERE submitted_at >= %s AND submitted_at < %s AND submission->>'type' = 'field_card'" % (lo, hi)),
            "work_approved": n("SELECT count(*) AS n FROM trials WHERE completed_at >= %s AND completed_at < %s" % (lo, hi)),
            "money_invoiced": total("SELECT sum(amount) AS n FROM invoices WHERE status <> 'Void' AND created_at >= %s AND created_at < %s" % (lo, hi)),
            "money_received": total("SELECT sum(amount) AS n FROM invoices WHERE status = 'Paid' AND paid_at >= %s AND paid_at < %s" % (lo, hi)),
            "paid_to_youth": total("SELECT sum(amount) AS n FROM payouts WHERE status = 'Paid' AND paid_at >= %s AND paid_at < %s" % (lo, hi)),
        }
        r["places"] = [
            {"location": row["loc"], "people": row["c"]}
            for row in db.execute(
                "SELECT coalesce(nullif(trim(location), ''), 'Not given') AS loc, count(*) AS c FROM youth "
                "WHERE deleted_at IS NULL AND created_at >= %s AND created_at < %s GROUP BY 1 ORDER BY c DESC, loc LIMIT 10" % (lo, hi),
                (start, end),
            ).fetchall()
        ]
        town = "coalesce(nullif(trim(%s.location), ''), 'Not given')"
        jobs = {row["t"]: row["n"] for row in db.execute(
            "SELECT " + town % "b" + " AS t, count(*) AS n FROM opportunities o JOIN businesses b ON b.id = o.business_id "
            "WHERE o.created_at >= %s AND o.created_at < %s GROUP BY 1" % (lo, hi), (start, end)).fetchall()}
        done = {row["t"]: row["n"] for row in db.execute(
            "SELECT " + town % "b" + " AS t, count(*) AS n FROM trials t JOIN opportunity_assignments oa ON oa.id = t.assignment_id "
            "JOIN opportunities o ON o.id = oa.opportunity_id JOIN businesses b ON b.id = o.business_id "
            "WHERE t.completed_at >= %s AND t.completed_at < %s GROUP BY 1" % (lo, hi), (start, end)).fetchall()}
        paid = {row["t"]: float(row["n"] or 0) for row in db.execute(
            "SELECT " + town % "b" + " AS t, sum(i.amount) AS n FROM invoices i JOIN businesses b ON b.id = i.business_id "
            "WHERE i.status = 'Paid' AND i.paid_at >= %s AND i.paid_at < %s GROUP BY 1" % (lo, hi), (start, end)).fetchall()}
        names = sorted(set(jobs) | set(done) | set(paid), key=lambda t: (-jobs.get(t, 0), t))[:15]
        r["towns"] = [{"town": t, "jobs": jobs.get(t, 0), "approved": done.get(t, 0), "money": paid.get(t, 0.0)} for t in names]
        r["agents"] = [
            {"name": row["name"], "registered": row["registered"], "chose_own_password": row["active"]}
            for row in db.execute(
                "SELECT coalesce(s.name, 'Admin key') AS name, count(*) AS registered, "
                "count(*) FILTER (WHERE NOT y.must_change_password) AS active "
                "FROM youth y LEFT JOIN staff s ON s.id::text = y.registered_by "
                "WHERE y.deleted_at IS NULL AND y.registered_by IS NOT NULL AND y.created_at >= %s AND y.created_at < %s "
                "GROUP BY 1 ORDER BY registered DESC, name" % (lo, hi),
                (start, end),
            ).fetchall()
        ]
        # all-time standing, so a quiet month still shows the base
        r["total"] = {
            "people": db.execute("SELECT count(*) AS n FROM youth WHERE deleted_at IS NULL").fetchone()["n"],
            "businesses": db.execute("SELECT count(*) AS n FROM businesses").fetchone()["n"],
            "verified_skills": db.execute("SELECT count(*) AS n FROM youth_capabilities yc JOIN youth y ON y.id = yc.youth_id WHERE yc.verified AND y.deleted_at IS NULL").fetchone()["n"],
            "jobs_done": db.execute("SELECT count(*) AS n FROM opportunities WHERE status = 'Completed'").fetchone()["n"],
        }
    return r


def report_text(r):
    """Plain text a person can paste into WhatsApp or a funder update."""
    t = r["total"]
    return "\n".join([
        "BSTM Activation, %s" % r["month"],
        "New people: %d · New businesses: %d" % (r["people_joined"], r["businesses_joined"]),
        "Jobs posted: %d · Work submitted: %d · Work approved: %d · Field cards: %d" % (r["jobs_posted"], r["work_submitted"], r["work_approved"], r["field_cards"]),
        "Money received: P%.2f · Paid to young people: P%.2f" % (r["money_received"], r["paid_to_youth"]),
        "All time: %d people, %d businesses, %d verified skills, %d jobs done" % (t["people"], t["businesses"], t["verified_skills"], t["jobs_done"]),
    ])


def report_csv(r):
    """The same numbers as a spreadsheet-ready CSV (metric,value)."""
    rows = [("month", r["month"])]
    for k in ("people_joined", "businesses_joined", "jobs_posted", "work_submitted", "field_cards", "work_approved",
              "money_invoiced", "money_received", "paid_to_youth"):
        rows.append((k, r[k]))
    rows += [("place: " + p["location"], p["people"]) for p in r["places"]]
    rows += [("town: " + t["town"] + " jobs", t["jobs"]) for t in r["towns"]]
    rows += [("agent: " + a["name"] + " registered", a["registered"]) for a in r["agents"]]
    rows += [("total_" + k, v) for k, v in r["total"].items()]
    esc = lambda v: '"' + str(v).replace('"', '""') + '"'
    return "metric,value\n" + "\n".join(esc(a) + "," + esc(b) for a, b in rows) + "\n"
