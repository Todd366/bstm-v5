"""Payments ledger: invoices (what a business owes), payments (money in),
payouts (money out to youth), payout accounts.

Rules (Production Signature: integration + evidence):
  * One invoice per completed assignment; shares always sum to the amount.
  * A payment is Submitted by the business (or staff), then Confirmed or
    Rejected by staff. Only confirmed money counts.
  * The same (provider, provider_ref) can never be recorded twice.
  * Idempotency keys make retried requests safe.
  * A youth payout is created only once the invoice is fully paid.
  * Every state change is written to `activity` and notifies the people
    concerned, inside the same transaction.
"""

import json
from decimal import ROUND_HALF_UP, Decimal

import psycopg2

from app.core.errors import Conflict
from app.core.validation import clean_text, require_uuid
from app.db.database import transaction
from app.services.notification_service import notify
from app.services.payment_providers import get_provider

PAYMENT_METHODS = ("MyZaka", "OrangeMoney", "BankEFT", "Cash", "Card", "Other")
PAYOUT_METHODS = ("MyZaka", "OrangeMoney", "BankEFT", "Other")
TWO = Decimal("0.01")


def money(value):
    try:
        return Decimal(str(value)).quantize(TWO, rounding=ROUND_HALF_UP)
    except Exception:
        raise ValueError("Amount must be a number")


def _log(db, event, actor_id, target_id, details):
    db.execute(
        "INSERT INTO activity (event, actor_id, target_id, details) VALUES (?, ?, ?, ?)",
        (event, actor_id, target_id, json.dumps(details, default=str)),
    )


def _pula(amount):
    return "P{:,.2f}".format(Decimal(str(amount)))


# ---------- invoices ----------

def create_invoice_in_tx(db, assignment_id, business_id, youth_id, opportunity_id, budget, youth_share_rate):
    """Called from complete_assignment's transaction. Returns the invoice
    id, or None when there is nothing to bill."""

    amount = money(budget)

    if not business_id or amount <= 0:
        return None

    youth_share = (amount * Decimal(str(youth_share_rate))).quantize(TWO, rounding=ROUND_HALF_UP)
    platform_share = amount - youth_share

    row = db.execute(
        """
        INSERT INTO invoices (
            reference, business_id, opportunity_id, assignment_id, youth_id,
            amount, youth_share, platform_share
        )
        VALUES ('BSTM-' || nextval('invoice_ref_seq'), ?, ?, ?, ?, ?, ?, ?)
        RETURNING id, reference
        """,
        (business_id, opportunity_id, assignment_id, youth_id, amount, youth_share, platform_share),
    ).fetchone()

    _log(db, "invoice_issued", business_id, row["id"],
         {"reference": row["reference"], "amount": amount, "youth_share": youth_share})

    notify(db, "business", business_id, "invoice_issued", "Invoice " + row["reference"],
           "Work is complete. Please pay " + _pula(amount) + " and submit the payment reference.")
    notify(db, "youth", youth_id, "job_completed", "Job completed",
           "You earned " + _pula(youth_share) + ". Your payout is prepared once the business pays.")

    return str(row["id"])


_INVOICE_COLUMNS = """
    i.id, i.reference, i.business_id, b.name AS business_name,
    i.opportunity_id, o.title AS opportunity_title, i.youth_id,
    i.amount, i.youth_share, i.platform_share, i.currency, i.status,
    i.created_at, i.paid_at
"""


def list_invoices(business_id=None, status=None, limit=50, offset=0):
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    clauses, params = [], []

    if business_id:
        clauses.append("i.business_id = ?")
        params.append(require_uuid(business_id, "Business"))

    if status:
        if status not in ("Issued", "Paid", "Void"):
            raise ValueError("Invalid invoice status")
        clauses.append("i.status = ?")
        params.append(status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    with transaction() as db:
        rows = db.execute(
            f"""
            SELECT {_INVOICE_COLUMNS},
                   COALESCE((SELECT sum(p.amount) FROM payments p
                             WHERE p.invoice_id = i.id AND p.status = 'Confirmed'), 0) AS paid_amount,
                   (SELECT count(*) FROM payments p
                    WHERE p.invoice_id = i.id AND p.status = 'Submitted') AS pending_payments
            FROM invoices i
            JOIN businesses b ON b.id = i.business_id
            LEFT JOIN opportunities o ON o.id = i.opportunity_id
            {where}
            ORDER BY i.created_at DESC LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]


# ---------- payments (money in) ----------

def submit_payment(
    invoice_id, method, provider_ref=None, amount=None, submitted_by="staff",
    business_id=None, idempotency_key=None, note=None, provider="manual",
):
    invoice_id = require_uuid(invoice_id, "Invoice")

    if method not in PAYMENT_METHODS:
        raise ValueError("Choose a payment method")

    provider_ref = clean_text(provider_ref, "Payment reference", 80, required=method != "Cash")
    note = clean_text(note, "Note", 300, required=False)
    idempotency_key = clean_text(idempotency_key, "Idempotency key", 100, required=False)

    if provider_ref is not None and len(provider_ref) < 4:
        raise ValueError("Payment reference is too short")

    try:
        with transaction() as db:

            if idempotency_key:
                existing = db.execute(
                    "SELECT id FROM payments WHERE idempotency_key = ?", (idempotency_key,)
                ).fetchone()
                if existing:
                    return str(existing["id"])

            invoice = db.execute(
                "SELECT id, reference, business_id, amount, status FROM invoices WHERE id = ? FOR UPDATE",
                (invoice_id,),
            ).fetchone()

            if not invoice or (business_id and str(invoice["business_id"]) != str(business_id)):
                raise ValueError("Invoice not found")

            if invoice["status"] != "Issued":
                raise Conflict("This invoice is not open for payment")

            counted = db.execute(
                """
                SELECT COALESCE(sum(amount), 0) AS s FROM payments
                WHERE invoice_id = ? AND status IN ('Submitted', 'Confirmed')
                """,
                (invoice_id,),
            ).fetchone()["s"]

            remaining = Decimal(str(invoice["amount"])) - Decimal(str(counted))

            if remaining <= 0:
                raise Conflict("Payments for this invoice are already submitted")

            amount = remaining if amount in (None, "") else money(amount)

            if amount <= 0:
                raise ValueError("Amount must be more than zero")

            if amount > remaining:
                raise ValueError("Amount is more than the " + _pula(remaining) + " still owed")

            row = db.execute(
                """
                INSERT INTO payments (
                    invoice_id, amount, method, provider, provider_ref,
                    idempotency_key, submitted_by, note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (invoice_id, amount, method, provider, provider_ref, idempotency_key, submitted_by, note),
            ).fetchone()

            _log(db, "payment_submitted", invoice["business_id"], row["id"],
                 {"invoice": invoice["reference"], "amount": amount, "method": method,
                  "provider": provider, "provider_ref": provider_ref})

    except psycopg2.errors.UniqueViolation:
        raise Conflict("This payment reference has already been used")

    return str(row["id"])


def confirm_payment(payment_id, confirmed_by="staff"):
    payment_id = require_uuid(payment_id, "Payment")

    with transaction() as db:

        payment = db.execute(
            "SELECT id, invoice_id, amount, status FROM payments WHERE id = ? FOR UPDATE",
            (payment_id,),
        ).fetchone()

        if not payment:
            raise ValueError("Payment not found")

        if payment["status"] != "Submitted":
            raise Conflict("Only submitted payments can be confirmed")

        invoice = db.execute(
            """
            SELECT id, reference, business_id, youth_id, amount, youth_share, status
            FROM invoices WHERE id = ? FOR UPDATE
            """,
            (payment["invoice_id"],),
        ).fetchone()

        db.execute(
            "UPDATE payments SET status = 'Confirmed', confirmed_by = ?, confirmed_at = now() WHERE id = ?",
            (confirmed_by, payment_id),
        )

        confirmed = Decimal(str(db.execute(
            "SELECT COALESCE(sum(amount), 0) AS s FROM payments WHERE invoice_id = ? AND status = 'Confirmed'",
            (invoice["id"],),
        ).fetchone()["s"]))

        _log(db, "payment_confirmed", invoice["business_id"], payment_id,
             {"invoice": invoice["reference"], "amount": payment["amount"], "confirmed_by": confirmed_by})

        paid_in_full = invoice["status"] == "Issued" and confirmed >= Decimal(str(invoice["amount"]))

        if paid_in_full:
            db.execute("UPDATE invoices SET status = 'Paid', paid_at = now() WHERE id = ?", (invoice["id"],))
            _create_payout(db, invoice)

        notify(db, "business", invoice["business_id"], "payment_confirmed",
               "Payment confirmed",
               _pula(payment["amount"]) + " received for " + invoice["reference"] + ("." if not paid_in_full else ". Invoice paid in full. Thank you."))

    return str(payment_id)


def reject_payment(payment_id, note=None, rejected_by="staff"):
    payment_id = require_uuid(payment_id, "Payment")
    note = clean_text(note, "Reason", 300, required=False)

    with transaction() as db:

        payment = db.execute(
            """
            SELECT p.id, p.status, p.amount, i.reference, i.business_id
            FROM payments p JOIN invoices i ON i.id = p.invoice_id
            WHERE p.id = ? FOR UPDATE OF p
            """,
            (payment_id,),
        ).fetchone()

        if not payment:
            raise ValueError("Payment not found")

        if payment["status"] != "Submitted":
            raise Conflict("Only submitted payments can be rejected")

        db.execute(
            "UPDATE payments SET status = 'Rejected', confirmed_by = ?, confirmed_at = now(), note = COALESCE(?, note) WHERE id = ?",
            (rejected_by, note, payment_id),
        )

        _log(db, "payment_rejected", payment["business_id"], payment_id,
             {"invoice": payment["reference"], "reason": note})

        notify(db, "business", payment["business_id"], "payment_rejected", "Payment not confirmed",
               "We could not confirm your payment for " + payment["reference"] + "." + ((" Reason: " + note) if note else " Please check the reference and submit again."))

    return str(payment_id)


def list_payments(status=None, limit=50, offset=0):
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    if status and status not in ("Submitted", "Confirmed", "Rejected"):
        raise ValueError("Invalid payment status")

    with transaction() as db:
        rows = db.execute(
            """
            SELECT p.id, p.invoice_id, i.reference AS invoice_reference, b.name AS business_name,
                   p.amount, p.method, p.provider, p.provider_ref, p.status,
                   p.submitted_by, p.confirmed_by, p.note, p.created_at, p.confirmed_at
            FROM payments p
            JOIN invoices i ON i.id = p.invoice_id
            JOIN businesses b ON b.id = i.business_id
            WHERE (?::text IS NULL OR p.status = ?)
            ORDER BY p.created_at DESC LIMIT ? OFFSET ?
            """,
            (status, status, limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]


def _park_unmatched(provider_name, event, reason):
    """Money may have arrived that we cannot attach to an open invoice:
    keep it for staff instead of failing silently."""

    ref = str(event.get("provider_ref") or "")[:80] or "unknown"

    try:
        amount = money(event.get("amount")) if event.get("amount") not in (None, "") else None
    except ValueError:
        amount = None

    with transaction() as db:
        db.execute(
            """
            INSERT INTO unmatched_payments (provider, provider_ref, invoice_reference, amount, method, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (provider, provider_ref) DO NOTHING
            """,
            (provider_name, ref, str(event.get("invoice_reference") or "")[:40] or None, amount,
             str(event.get("method") or "")[:20] or None, reason),
        )
        _log(db, "payment_unmatched", None, None, {"provider": provider_name, "provider_ref": ref, "reason": reason})

    return None


def record_provider_payment(provider_name, event):
    """Idempotent ingestion of an authenticated provider event: records
    and confirms the payment. Returns the payment id, or None when the
    event was parked for staff (unknown / already paid / over-payment)."""

    provider = get_provider(provider_name)

    reference = clean_text(event.get("invoice_reference"), "Invoice reference", 40)
    provider_ref = clean_text(event.get("provider_ref"), "Provider reference", 80)
    method = event.get("method") if event.get("method") in PAYMENT_METHODS else "Other"

    with transaction() as db:
        invoice = db.execute("SELECT id FROM invoices WHERE reference = ?", (reference,)).fetchone()
        duplicate = db.execute(
            "SELECT id FROM payments WHERE provider = ? AND provider_ref = ? AND status <> 'Rejected'",
            (provider.name, provider_ref),
        ).fetchone()

    if duplicate:
        return str(duplicate["id"])

    if not invoice:
        return _park_unmatched(provider.name, event, "No invoice with that reference")

    try:
        payment_id = submit_payment(
            str(invoice["id"]), method, provider_ref=provider_ref, amount=event.get("amount"),
            submitted_by="provider:" + provider.name, idempotency_key=provider.name + ":" + provider_ref,
            provider=provider.name,
        )
    except (ValueError, Conflict) as exc:
        return _park_unmatched(provider.name, event, str(exc))

    confirm_payment(payment_id, confirmed_by="provider:" + provider.name)

    return payment_id


def list_unmatched(status="Open", limit=50):
    limit = max(1, min(int(limit), 200))

    with transaction() as db:
        rows = db.execute(
            """
            SELECT id, provider, provider_ref, invoice_reference, amount, method, reason,
                   status, resolution, created_at, resolved_at
            FROM unmatched_payments WHERE (?::text IS NULL OR status = ?)
            ORDER BY created_at DESC LIMIT ?
            """,
            (status, status, limit),
        ).fetchall()

    return [dict(r) for r in rows]


def resolve_unmatched(unmatched_id, resolution):
    unmatched_id = require_uuid(unmatched_id, "Record")
    resolution = clean_text(resolution, "What was done", 300)

    with transaction() as db:
        row = db.execute(
            "UPDATE unmatched_payments SET status = 'Resolved', resolution = ?, resolved_at = now() "
            "WHERE id = ? AND status = 'Open' RETURNING id",
            (resolution, unmatched_id),
        ).fetchone()

        if not row:
            raise ValueError("Record not found")

        _log(db, "unmatched_resolved", None, unmatched_id, {"resolution": resolution})

    return {"id": unmatched_id, "status": "Resolved"}


# ---------- payouts (money out) ----------

def _create_payout(db, invoice):
    if not invoice["youth_id"] or Decimal(str(invoice["youth_share"])) <= 0:
        return None

    account = db.execute(
        "SELECT method, account_name, account_ref FROM payout_accounts WHERE youth_id = ?",
        (invoice["youth_id"],),
    ).fetchone()

    destination = (account["account_name"] + " · " + account["account_ref"]) if account else None

    row = db.execute(
        """
        INSERT INTO payouts (youth_id, invoice_id, amount, method, destination)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (invoice_id) WHERE status <> 'Failed' DO NOTHING
        RETURNING id
        """,
        (invoice["youth_id"], invoice["id"], invoice["youth_share"],
         account["method"] if account else None, destination),
    ).fetchone()

    if row is None:
        return None

    _log(db, "payout_created", invoice["youth_id"], row["id"],
         {"invoice": invoice["reference"], "amount": invoice["youth_share"]})

    notify(db, "youth", invoice["youth_id"], "payout_pending", "Your payout is being prepared",
           _pula(invoice["youth_share"]) + " is ready to be sent to you." +
           ("" if account else " Add your payout details in Earnings so we can pay you."))

    return str(row["id"])


def mark_payout_paid(payout_id, provider_ref, paid_by="staff"):
    payout_id = require_uuid(payout_id, "Payout")
    provider_ref = clean_text(provider_ref, "Payout reference", 80)

    with transaction() as db:

        payout = db.execute(
            "SELECT id, youth_id, amount, status, destination FROM payouts WHERE id = ? FOR UPDATE",
            (payout_id,),
        ).fetchone()

        if not payout:
            raise ValueError("Payout not found")

        if payout["status"] != "Pending":
            raise Conflict("Only pending payouts can be marked paid")

        if not payout["destination"]:
            raise ValueError("The youth has not added payout details yet")

        db.execute(
            "UPDATE payouts SET status = 'Paid', provider_ref = ?, paid_at = now(), paid_by = ? WHERE id = ?",
            (provider_ref, paid_by, payout_id),
        )

        # Revenue means money actually sent to the youth.
        db.execute(
            "UPDATE youth SET revenue = revenue + ? WHERE id = ?",
            (payout["amount"], payout["youth_id"]),
        )

        _log(db, "payout_paid", payout["youth_id"], payout_id,
             {"amount": payout["amount"], "provider_ref": provider_ref, "paid_by": paid_by})

        notify(db, "youth", payout["youth_id"], "payout_paid", "You have been paid",
               _pula(payout["amount"]) + " was sent to " + payout["destination"] + ". Reference: " + provider_ref)

    return str(payout_id)


def fail_payout(payout_id, note=None):
    """Marks a payout Failed and re-queues a fresh Pending one."""

    payout_id = require_uuid(payout_id, "Payout")
    note = clean_text(note, "Reason", 300, required=False)

    with transaction() as db:

        payout = db.execute(
            "SELECT id, youth_id, invoice_id, status FROM payouts WHERE id = ? FOR UPDATE",
            (payout_id,),
        ).fetchone()

        if not payout:
            raise ValueError("Payout not found")

        if payout["status"] != "Pending":
            raise Conflict("Only pending payouts can be marked failed")

        db.execute("UPDATE payouts SET status = 'Failed' WHERE id = ?", (payout_id,))

        invoice = db.execute(
            "SELECT id, reference, youth_id, youth_share FROM invoices WHERE id = ?",
            (payout["invoice_id"],),
        ).fetchone()

        _log(db, "payout_failed", payout["youth_id"], payout_id, {"reason": note})
        _create_payout(db, invoice)

    return str(payout_id)


def list_payouts(status=None, youth_id=None, limit=50, offset=0):
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    if status and status not in ("Pending", "Paid", "Failed"):
        raise ValueError("Invalid payout status")

    youth_id = require_uuid(youth_id, "Youth") if youth_id else None

    with transaction() as db:
        rows = db.execute(
            """
            SELECT po.id, po.youth_id, y.name AS youth_name, po.invoice_id,
                   i.reference AS invoice_reference, po.amount, po.method,
                   po.destination, po.provider_ref, po.status, po.created_at, po.paid_at
            FROM payouts po
            JOIN youth y ON y.id = po.youth_id
            JOIN invoices i ON i.id = po.invoice_id
            WHERE (?::text IS NULL OR po.status = ?)
              AND (?::uuid IS NULL OR po.youth_id = ?::uuid)
            ORDER BY po.created_at DESC LIMIT ? OFFSET ?
            """,
            (status, status, youth_id, youth_id, limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]


# ---------- youth payout account + earnings ----------

def set_payout_account(youth_id, method, account_name, account_ref):
    youth_id = require_uuid(youth_id, "Youth")

    if method not in PAYOUT_METHODS:
        raise ValueError("Choose how you want to be paid")

    account_name = clean_text(account_name, "Account name", 120)
    account_ref = clean_text(account_ref, "Account number", 60)

    if len(account_ref) < 6:
        raise ValueError("Account number looks too short")

    with transaction() as db:
        db.execute(
            """
            INSERT INTO payout_accounts (youth_id, method, account_name, account_ref)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (youth_id) DO UPDATE
            SET method = EXCLUDED.method, account_name = EXCLUDED.account_name,
                account_ref = EXCLUDED.account_ref, updated_at = now()
            """,
            (youth_id, method, account_name, account_ref),
        )

        destination = account_name + " · " + account_ref

        db.execute(
            """
            UPDATE payouts SET method = ?, destination = ?
            WHERE youth_id = ? AND status = 'Pending'
            """,
            (method, destination, youth_id),
        )

        _log(db, "payout_account_updated", youth_id, youth_id, {"method": method})

    return {"status": "saved"}


def get_payout_account(youth_id):
    youth_id = require_uuid(youth_id, "Youth")

    with transaction() as db:
        row = db.execute(
            "SELECT method, account_name, account_ref FROM payout_accounts WHERE youth_id = ?",
            (youth_id,),
        ).fetchone()

    return dict(row) if row else None


def youth_earnings(youth_id):
    youth_id = require_uuid(youth_id, "Youth")

    with transaction() as db:
        totals = db.execute(
            """
            SELECT
              COALESCE(sum(i.youth_share), 0) AS earned,
              COALESCE(sum(i.youth_share) FILTER (WHERE i.status = 'Issued'), 0) AS awaiting_business,
              COALESCE((SELECT sum(amount) FROM payouts WHERE youth_id = ? AND status = 'Pending'), 0) AS pending_payout,
              COALESCE((SELECT sum(amount) FROM payouts WHERE youth_id = ? AND status = 'Paid'), 0) AS paid_out
            FROM invoices i WHERE i.youth_id = ? AND i.status <> 'Void'
            """,
            (youth_id, youth_id, youth_id),
        ).fetchone()

        payouts = db.execute(
            """
            SELECT po.id, po.amount, po.status, po.destination, po.provider_ref,
                   po.created_at, po.paid_at, i.reference AS invoice_reference,
                   o.title AS opportunity_title
            FROM payouts po
            JOIN invoices i ON i.id = po.invoice_id
            LEFT JOIN opportunities o ON o.id = i.opportunity_id
            WHERE po.youth_id = ? ORDER BY po.created_at DESC LIMIT 50
            """,
            (youth_id,),
        ).fetchall()

    return {"totals": dict(totals), "payouts": [dict(p) for p in payouts]}
