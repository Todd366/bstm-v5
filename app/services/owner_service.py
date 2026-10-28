"""Owner tools: review every record, correct it, or remove it. Only the
owner (see BSTM_OWNER_EMAIL) can reach these routes.

Rules that keep the books honest:
  * Money records (invoices, payments, payouts) are never deleted. A person
    or business that has any cannot be removed until the money is settled and
    the invoice voided by staff; the answer says why.
  * Every change and deletion is written to the activity log with who did it.
  * Deletion needs the exact word DELETE, and works on a chosen list only.
"""

import json
import re

from app.core.errors import Conflict
from app.core.validation import clean_text, require_uuid
from app.db.database import transaction

KINDS = ("youth", "businesses", "jobs")
_TEST_WORDS = re.compile(r"\b(test|testing|demo|sample|fake|placeholder|dummy|mock)\b", re.I)
_TEST_EMAIL = re.compile(r"@(example\.(com|org|net)|test\.|mailinator)", re.I)


def _suspect(name, email, can_login):
    reasons = []
    if _TEST_WORDS.search(name or ""):
        reasons.append("name looks like a test")
    if email and _TEST_EMAIL.search(email):
        reasons.append("test email address")
    if can_login is False:
        reasons.append("cannot log in (old record, no email or password)")
    return reasons


def _log(db, event, actor, target, details):
    db.execute(
        "INSERT INTO activity (event, actor_id, target_id, details) VALUES (?, NULL, ?, ?)",
        (event, target, json.dumps(dict(details, by=actor), default=str)),
    )


def list_records(kind):
    if kind not in KINDS:
        raise ValueError("Choose youth, businesses or jobs")

    with transaction() as db:
        if kind == "youth":
            rows = db.execute(
                """
                SELECT y.id, y.name, y.email, y.location, y.created_at,
                       (y.password_hash IS NOT NULL) AS can_login,
                       (SELECT count(*) FROM opportunity_assignments a WHERE a.youth_id = y.id) AS jobs,
                       (SELECT count(*) FROM invoices i WHERE i.youth_id = y.id) AS money_records
                FROM youth y WHERE y.deleted_at IS NULL ORDER BY y.created_at
                """
            ).fetchall()
        elif kind == "businesses":
            rows = db.execute(
                """
                SELECT b.id, b.name, b.owner, b.email, b.location, b.sector, b.created_at,
                       (b.password_hash IS NOT NULL) AS can_login,
                       (SELECT count(*) FROM opportunities o WHERE o.business_id = b.id) AS jobs,
                       (SELECT count(*) FROM invoices i WHERE i.business_id = b.id) AS money_records
                FROM businesses b ORDER BY b.created_at
                """
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT o.id, o.title AS name, o.status, o.budget, o.department, b.name AS business, o.created_at,
                       (SELECT count(*) FROM opportunity_assignments a WHERE a.opportunity_id = o.id) AS people,
                       (SELECT count(*) FROM invoices i WHERE i.opportunity_id = o.id) AS money_records
                FROM opportunities o LEFT JOIN businesses b ON b.id = o.business_id ORDER BY o.created_at
                """
            ).fetchall()

    out = []
    for r in rows:
        r = dict(r)
        can_login = r.get("can_login")
        reasons = _suspect(r.get("name"), r.get("email"), can_login if kind != "jobs" else None)
        if kind == "jobs" and (r.get("business") or "").lower().find("test") >= 0:
            reasons.append("belongs to a test business")
        r["suggested_test"] = reasons
        out.append(r)
    return out


def _money_block(db, kind, rid):
    col = {"youth": "youth_id", "businesses": "business_id", "jobs": "opportunity_id"}[kind]
    n = db.execute("SELECT count(*) AS n FROM invoices WHERE " + col + " = ?", (rid,)).fetchone()["n"]
    return n


def delete_records(kind, ids, confirm, actor="owner"):
    if kind not in KINDS:
        raise ValueError("Choose youth, businesses or jobs")

    if confirm != "DELETE":
        raise ValueError('Type DELETE to confirm')

    if not isinstance(ids, list) or not ids or len(ids) > 100:
        raise ValueError("Choose between 1 and 100 records")

    ids = [require_uuid(i, "Record") for i in ids]
    removed, refused = [], []

    with transaction() as db:
        for rid in ids:
            table = {"youth": "youth", "businesses": "businesses", "jobs": "opportunities"}[kind]
            row = db.execute("SELECT id FROM " + table + " WHERE id = ? FOR UPDATE", (rid,)).fetchone()

            if not row:
                continue

            if _money_block(db, kind, rid):
                refused.append(rid)
                continue

            if kind == "businesses":
                # its jobs must go too (they would otherwise be left with no owner)
                jobs = [r["id"] for r in db.execute("SELECT id FROM opportunities WHERE business_id = ?", (rid,)).fetchall()]
                for jid in jobs:
                    if _money_block(db, "jobs", jid):
                        refused.append(rid)
                        break
                else:
                    for jid in jobs:
                        db.execute("DELETE FROM opportunities WHERE id = ?", (jid,))
                    db.execute("DELETE FROM notifications WHERE recipient_type = 'business' AND recipient_id = ?", (rid,))
                    db.execute("DELETE FROM password_resets WHERE account_type = 'business' AND account_id = ?", (rid,))
                    db.execute("DELETE FROM businesses WHERE id = ?", (rid,))
                    removed.append(rid)
                    _log(db, "owner_deleted_business", actor, rid, {"jobs_removed": len(jobs)})
                continue

            if kind == "youth":
                db.execute("DELETE FROM notifications WHERE recipient_type = 'youth' AND recipient_id = ?", (rid,))
                db.execute("DELETE FROM password_resets WHERE account_type = 'youth' AND account_id = ?", (rid,))
                db.execute("DELETE FROM youth WHERE id = ?", (rid,))
            else:
                db.execute("DELETE FROM opportunities WHERE id = ?", (rid,))

            removed.append(rid)
            _log(db, "owner_deleted_" + kind.rstrip("s"), actor, rid, {})

    return {"removed": removed, "kept_because_of_money": refused}


_EDITABLE = {
    "youth": {"name": 120, "location": 120, "goal": 300, "passion": 300, "availability": 100, "equipment": 300, "bio": 500, "email": 254},
    "businesses": {"name": 120, "owner": 120, "sector": 60, "location": 120, "main_problem": 500, "email": 254},
    "jobs": {"title": 200, "description": 2000, "department": 100},
}
_TABLE = {"youth": "youth", "businesses": "businesses", "jobs": "opportunities"}
_JOB_STATUSES = ("Open", "Matched", "Assigned", "InProgress", "Completed", "Cancelled")


def update_record(kind, rid, data, actor="owner"):
    if kind not in KINDS:
        raise ValueError("Choose youth, businesses or jobs")

    rid = require_uuid(rid, "Record")
    fields = _EDITABLE[kind]
    changes = {}

    for key, limit in fields.items():
        if key in data and data[key] is not None:
            value = clean_text(data[key], key.capitalize(), limit, required=key in ("name", "title"))
            if key == "email":
                value = (value or "").strip().lower() or None
            changes[key] = value

    if kind == "jobs":
        if data.get("budget") is not None:
            try:
                budget = float(data["budget"])
            except (TypeError, ValueError):
                raise ValueError("Budget must be a number")
            if budget < 0 or budget > 10_000_000:
                raise ValueError("Budget is out of range")
            changes["budget"] = budget
        if data.get("status") is not None:
            if data["status"] not in _JOB_STATUSES:
                raise ValueError("Unknown status")
            changes["status"] = data["status"]

    if not changes:
        raise ValueError("Nothing to change")

    sets = ", ".join(k + " = ?" for k in changes)

    with transaction() as db:
        existing = db.execute("SELECT id FROM " + _TABLE[kind] + " WHERE id = ? FOR UPDATE", (rid,)).fetchone()
        if not existing:
            raise ValueError("Record not found")

        try:
            db.execute("UPDATE " + _TABLE[kind] + " SET " + sets + ", updated_at = now() WHERE id = ?",
                       tuple(changes.values()) + (rid,))
        except Exception as exc:  # noqa: BLE001
            if exc.__class__.__name__ == "UniqueViolation":
                raise Conflict("Another record already uses that name or email")
            raise

        _log(db, "owner_edited_" + kind.rstrip("s"), actor, rid, {"fields": sorted(changes)})

    return {"status": "updated", "id": rid}
