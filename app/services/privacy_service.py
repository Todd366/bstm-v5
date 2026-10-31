"""A person's right to their own data: export everything held about a
youth, and delete the account. Deleting removes personal details but keeps
the financial and work records the business and the ledger need."""

import json

from app.core.errors import Conflict, Forbidden
from app.core.validation import require_uuid
from app.db.database import transaction
from app.services.auth_service import verify_password


def export_youth(youth_id):
    youth_id = require_uuid(youth_id, "Youth")

    queries = {
        "profile": "SELECT id, name, location, passion, goal, availability, equipment, level, capability_score, "
                   "learning_score, reputation_score, reliability_score, completed_trials, revenue, email, phone, registered_by, intake, bio, "
                   "public_profile, created_at FROM youth WHERE id = ?",
        "capabilities": "SELECT * FROM youth_capabilities WHERE youth_id = ?",
        "assignments": "SELECT * FROM opportunity_assignments WHERE youth_id = ?",
        "trials": "SELECT t.* FROM trials t JOIN opportunity_assignments oa ON oa.id = t.assignment_id WHERE oa.youth_id = ?",
        "evidence": "SELECT * FROM evidence WHERE youth_id = ?",
        "invoices": "SELECT reference, amount, youth_share, status, created_at, paid_at FROM invoices WHERE youth_id = ?",
        "payouts": "SELECT amount, method, status, created_at, paid_at FROM payouts WHERE youth_id = ?",
        "payout_account": "SELECT method, account_name, account_ref FROM payout_accounts WHERE youth_id = ?",
        "notifications": "SELECT kind, title, body, created_at FROM notifications WHERE recipient_type = 'youth' AND recipient_id = ?",
    }

    out = {}

    with transaction() as db:
        for key, sql in queries.items():
            rows = db.execute(sql, (youth_id,)).fetchall()
            out[key] = [dict(r) for r in rows]

    if not out["profile"]:
        raise ValueError("Youth not found")

    out["profile"] = out["profile"][0]
    return json.loads(json.dumps(out, default=str))


def delete_youth(youth_id, password):
    youth_id = require_uuid(youth_id, "Youth")

    with transaction() as db:
        row = db.execute(
            "SELECT id, password_hash, deleted_at FROM youth WHERE id = ? FOR UPDATE", (youth_id,)
        ).fetchone()

        if not row or row["deleted_at"]:
            raise ValueError("Youth not found")

        if not isinstance(password, str) or not row["password_hash"] or not verify_password(password, row["password_hash"]):
            raise Forbidden("Password is not correct")

        busy = db.execute(
            "SELECT count(*) AS n FROM opportunity_assignments WHERE youth_id = ? AND status = 'Accepted'", (youth_id,)
        ).fetchone()["n"]
        owed = db.execute(
            "SELECT (SELECT count(*) FROM invoices WHERE youth_id = ? AND status = 'Issued') + "
            "(SELECT count(*) FROM payouts WHERE youth_id = ? AND status = 'Pending') AS n",
            (youth_id, youth_id),
        ).fetchone()["n"]

        if busy or owed:
            raise Conflict("You have a job in progress or money still to be settled. Finish or settle it first, "
                           "then you can delete your account.")

        db.execute(
            "UPDATE opportunity_assignments SET status = 'Cancelled' WHERE youth_id = ? AND status = 'Pending'",
            (youth_id,),
        )
        db.execute("DELETE FROM payout_accounts WHERE youth_id = ?", (youth_id,))
        db.execute("DELETE FROM notifications WHERE recipient_type = 'youth' AND recipient_id = ?", (youth_id,))
        db.execute("DELETE FROM youth_capabilities WHERE youth_id = ?", (youth_id,))
        db.execute(
            """
            UPDATE youth SET name = 'Deleted member', location = 'Deleted', goal = 'Deleted', passion = NULL,
                availability = NULL, equipment = NULL, intake = NULL, bio = NULL, public_profile = false,
                email = NULL, phone = NULL, registered_by = NULL, must_change_password = false, password_hash = NULL, deleted_at = now(), updated_at = now()
            WHERE id = ?
            """,
            (youth_id,),
        )
        db.execute(
            "INSERT INTO activity (event, actor_id, target_id, details) VALUES ('youth_deleted', ?, ?, '{}')",
            (youth_id, youth_id),
        )

    return {"status": "deleted"}
