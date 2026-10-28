"""Honest system check for staff: each line is something measured right
now (OK / WARN / FAIL) with the measurement, not a claim."""

from app.core.config import API_KEY, ENVIRONMENT, JWT_SECRET, PAY_INSTRUCTIONS
from app.db.database import transaction
from app.services import migration_service


def _c(name, status, detail):
    return {"name": name, "status": status, "detail": detail}


def scorecard():
    checks = []

    checks.append(_c("Environment", "OK" if ENVIRONMENT == "production" else "WARN", ENVIRONMENT))
    checks.append(_c("Token secret", "OK" if JWT_SECRET and len(JWT_SECRET) >= 32 else "FAIL",
                     "set, %d characters" % len(JWT_SECRET) if JWT_SECRET else "not set"))
    checks.append(_c("Break-glass admin key", "OK" if API_KEY and len(API_KEY) >= 24 else "WARN",
                     "set, %d characters" % len(API_KEY) if API_KEY else "not set"))
    checks.append(_c("Payment instructions", "OK" if PAY_INSTRUCTIONS and "BSTM_PAY" not in PAY_INSTRUCTIONS else "WARN",
                     "shown to businesses on invoices"))

    try:
        st = migration_service.status()
        pending = st.get("pending") or []
        checks.append(_c("Database updates", "OK" if not pending else "FAIL",
                         "up to date" if not pending else "%d waiting: tap Update database" % len(pending)))
    except Exception as exc:  # noqa: BLE001
        checks.append(_c("Database updates", "FAIL", type(exc).__name__))

    try:
        with transaction() as db:
            admins = db.execute("SELECT count(*) AS n FROM staff WHERE role = 'admin' AND active").fetchone()["n"]
        checks.append(_c("Named admin accounts", "OK" if admins else "WARN",
                         "%d active" % admins if admins else "none yet: everyone is using the shared key"))
    except Exception:  # noqa: BLE001
        checks.append(_c("Named admin accounts", "FAIL", "staff table missing: update the database"))

    with transaction() as db:
        def one(sql):
            return db.execute(sql).fetchone()["n"]

        stuck = one("SELECT count(*) AS n FROM payments WHERE status = 'Submitted' AND created_at < now() - interval '2 days'")
        checks.append(_c("Payments waiting over 2 days", "OK" if not stuck else "WARN", str(stuck)))

        old_payouts = one("SELECT count(*) AS n FROM payouts WHERE status = 'Pending' AND created_at < now() - interval '3 days'")
        checks.append(_c("Youth payouts waiting over 3 days", "OK" if not old_payouts else "WARN", str(old_payouts)))

        unmatched = one("SELECT count(*) AS n FROM unmatched_payments WHERE status = 'Open'")
        checks.append(_c("Unmatched money", "OK" if not unmatched else "WARN", str(unmatched)))

        overdue = one("SELECT count(*) AS n FROM invoices WHERE status = 'Issued' AND created_at < now() - interval '14 days'")
        checks.append(_c("Invoices unpaid over 14 days", "OK" if not overdue else "WARN", str(overdue)))

        pending_jobs = one("SELECT count(*) AS n FROM opportunities WHERE approval_status = 'Pending'")
        checks.append(_c("Jobs awaiting approval", "OK" if not pending_jobs else "WARN", str(pending_jobs)))

        # Money identity: confirmed payments never exceed what was invoiced.
        bad = one(
            "SELECT count(*) AS n FROM invoices i WHERE i.status <> 'Void' AND "
            "(SELECT COALESCE(sum(amount),0) FROM payments p WHERE p.invoice_id = i.id AND p.status = 'Confirmed') > i.amount"
        )
        checks.append(_c("Ledger balance", "OK" if not bad else "FAIL",
                         "no invoice is over-paid" if not bad else "%d invoice(s) over-paid" % bad))

    worst = "FAIL" if any(c["status"] == "FAIL" for c in checks) else ("WARN" if any(c["status"] == "WARN" for c in checks) else "OK")
    return {"overall": worst, "checks": checks}
