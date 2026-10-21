"""Payments ledger, business accounts, approvals, notifications, profiles."""

import hashlib
import hmac
import json

from app.core.errors import Conflict, Forbidden
from app.services import (
    assignment_service,
    business_service,
    notification_service,
    opportunity_service,
    payment_providers,
    payment_service,
    profile_service,
    queue_service,
)
from tests.helpers import create_youth, finish_work


def _completed_job(budget=1000, name="Ledger Shop"):
    """A business, a youth, a job worked and completed → invoice issued."""

    bid = business_service.create_business(name, "Owner", "Retail", "Maun", "x", email=name.replace(" ", "").lower() + "@example.com", password="correct-horse-battery")
    oid = opportunity_service.create_opportunity(bid, "Fix site", "d", None, budget)
    yid = create_youth(name="Worker " + name)
    aid = assignment_service.create_assignment(yid, oid, mode="application")
    assignment_service.accept_assignment(aid)
    finish_work(aid)
    invoice = payment_service.list_invoices(business_id=bid)[0]
    return bid, yid, aid, invoice


def test_completing_a_paid_job_issues_invoice_with_exact_shares(test_database):
    bid, yid, aid, invoice = _completed_job(1000)
    assert invoice["status"] == "Issued"
    assert float(invoice["amount"]) == 1000.0
    assert float(invoice["youth_share"]) == 700.0 and float(invoice["platform_share"]) == 300.0
    assert invoice["reference"].startswith("BSTM-")
    assert any(n["kind"] == "invoice_issued" for n in notification_service.list_notifications("business", bid)["items"])
    assert any(n["kind"] == "job_completed" for n in notification_service.list_notifications("youth", yid)["items"])


def test_free_job_creates_no_invoice(test_database):
    bid, yid, aid, _ = None, None, None, None
    b = business_service.create_business("Free Shop", "O", "Retail", "Maun", "x")
    o = opportunity_service.create_opportunity(b, "Volunteer", "d", None, 0)
    y = create_youth(name="Vol")
    a = assignment_service.create_assignment(y, o, mode="application")
    assignment_service.accept_assignment(a)
    finish_work(a)
    assert payment_service.list_invoices(business_id=b) == []


def test_full_money_flow_business_pays_staff_confirm_youth_paid(test_database):
    bid, yid, aid, invoice = _completed_job(1000)
    inv = invoice["id"]

    payment_service.set_payout_account(yid, "MyZaka", "Worker", "71234567")
    pid = payment_service.submit_payment(inv, "MyZaka", provider_ref="MZ12345678", submitted_by="business", business_id=bid)

    assert payment_service.list_payouts() == []                      # nothing paid out before confirmation
    payment_service.confirm_payment(pid)

    assert payment_service.list_invoices(business_id=bid)[0]["status"] == "Paid"
    payouts = payment_service.list_payouts(status="Pending")
    assert len(payouts) == 1 and float(payouts[0]["amount"]) == 700.0
    assert "71234567" in payouts[0]["destination"]

    payment_service.mark_payout_paid(payouts[0]["id"], "MZOUT0001")
    earnings = payment_service.youth_earnings(yid)["totals"]
    assert float(earnings["paid_out"]) == 700.0 and float(earnings["pending_payout"]) == 0.0
    assert any(n["kind"] == "payout_paid" for n in notification_service.list_notifications("youth", yid)["items"])


def test_payment_reference_cannot_be_reused_and_keys_are_idempotent(test_database):
    bid, yid, aid, invoice = _completed_job(1000, "Dup Shop")
    _, _, _, invoice2 = _completed_job(500, "Dup Shop Two")

    first = payment_service.submit_payment(invoice["id"], "OrangeMoney", provider_ref="OM-000111", amount=400, idempotency_key="k1")
    again = payment_service.submit_payment(invoice["id"], "OrangeMoney", provider_ref="OM-000111", amount=400, idempotency_key="k1")
    assert first == again                                            # retried request is harmless

    try:
        payment_service.submit_payment(invoice2["id"], "OrangeMoney", provider_ref="OM-000111")
        assert False, "same reference must be refused"
    except Conflict:
        pass


def test_overpayment_and_foreign_invoice_are_refused(test_database):
    bid, yid, aid, invoice = _completed_job(1000, "Over Shop")
    other = business_service.create_business("Other Shop", "O", "Retail", "Maun", "x")

    try:
        payment_service.submit_payment(invoice["id"], "BankEFT", provider_ref="EFT-99999", amount=5000)
        assert False
    except ValueError:
        pass

    try:
        payment_service.submit_payment(invoice["id"], "BankEFT", provider_ref="EFT-12345", business_id=other)
        assert False, "another business must not see this invoice"
    except ValueError as exc:
        assert "not found" in str(exc).lower()


def test_rejected_payment_does_not_pay_invoice_and_can_be_retried(test_database):
    bid, yid, aid, invoice = _completed_job(1000, "Rej Shop")
    pid = payment_service.submit_payment(invoice["id"], "MyZaka", provider_ref="BAD-00001")
    payment_service.reject_payment(pid, "No such transaction")
    assert payment_service.list_invoices(business_id=bid)[0]["status"] == "Issued"
    again = payment_service.submit_payment(invoice["id"], "MyZaka", provider_ref="BAD-00001")   # ref freed after rejection
    assert again != pid


def test_payout_waits_for_account_details(test_database):
    bid, yid, aid, invoice = _completed_job(1000, "NoAcct Shop")
    pid = payment_service.submit_payment(invoice["id"], "Cash")
    payment_service.confirm_payment(pid)
    payout = payment_service.list_payouts(status="Pending")[0]
    assert payout["destination"] is None
    try:
        payment_service.mark_payout_paid(payout["id"], "REF-0001")
        assert False
    except ValueError:
        pass
    payment_service.set_payout_account(yid, "BankEFT", "Worker", "1234567890")
    payment_service.mark_payout_paid(payout["id"], "REF-0001")      # now allowed: destination was back-filled


def test_provider_webhook_is_signed_idempotent_and_confirms(test_database):
    import os
    bid, yid, aid, invoice = _completed_job(1000, "Hook Shop")
    os.environ["BSTM_WEBHOOK_SECRET_SMS_BRIDGE"] = "s3cret-s3cret"
    body = json.dumps({"invoice_reference": invoice["reference"], "provider_ref": "SMS-777001", "amount": 1000, "method": "MyZaka"}).encode()
    good = hmac.new(b"s3cret-s3cret", body, hashlib.sha256).hexdigest()
    provider = payment_providers.get_provider("sms-bridge")

    try:
        provider.verify_webhook({"x-signature": "00" * 32}, body)
        assert False, "forged signature must be refused"
    except Forbidden:
        pass

    event = provider.verify_webhook({"x-signature": good}, body)
    first = payment_service.record_provider_payment("sms-bridge", event)
    second = payment_service.record_provider_payment("sms-bridge", event)   # provider retries
    assert first == second
    assert payment_service.list_invoices(business_id=bid)[0]["status"] == "Paid"
    assert len(payment_service.list_payouts()) == 1                          # paid out once, not twice


def test_business_account_login_and_no_password_leak(test_database):
    bid = business_service.create_business("Login Shop", "O", "Retail", "Maun", "x", email="owner@loginshop.bw", password="correct-horse-battery")
    assert business_service.authenticate_business("OWNER@loginshop.bw", "correct-horse-battery") == bid
    for bad in (("owner@loginshop.bw", "wrong-password-1"), ("nobody@x.bw", "correct-horse-battery")):
        try:
            business_service.authenticate_business(*bad)
            assert False
        except ValueError as exc:
            assert str(exc) == "Invalid email or password"
    assert "password_hash" not in business_service.get_business(bid)
    assert all("password_hash" not in b for b in business_service.list_businesses())


def test_business_jobs_need_approval_and_are_hidden_until_then(test_database):
    bid = business_service.create_business("Approve Shop", "O", "Retail", "Maun", "x")
    oid = opportunity_service.create_opportunity(bid, "Web design", "Build a web development site", None, 100, approval_status="Pending", created_by="business")
    yid = create_youth(name="Browser")

    assert opportunity_service.browse_open_opportunities(yid) == []
    try:
        assignment_service.create_assignment(yid, oid, mode="application")
        assert False, "pending job must not accept applications"
    except Conflict:
        pass
    assert len(queue_service.review_queue()["jobs"]) == 1

    opportunity_service.set_opportunity_approval(oid, True)
    assert [o["title"] for o in opportunity_service.browse_open_opportunities(yid)] == ["Web design"]
    assert any(n["kind"] == "job_approved" for n in notification_service.list_notifications("business", bid)["items"])

    oid2 = opportunity_service.create_opportunity(bid, "Bad job", "d", None, 0, approval_status="Pending", created_by="business")
    opportunity_service.set_opportunity_approval(oid2, False, "Not suitable")
    assert all(o["title"] != "Bad job" for o in opportunity_service.browse_open_opportunities(yid))


def test_business_sees_only_its_own_jobs_and_people(test_database):
    a = business_service.create_business("Biz A", "O", "Retail", "Maun", "x")
    b = business_service.create_business("Biz B", "O", "Retail", "Maun", "x")
    oa = opportunity_service.create_opportunity(a, "A job", "d", None, 0)
    opportunity_service.create_opportunity(b, "B job", "d", None, 0)
    assert [j["title"] for j in business_service.list_own_opportunities(a)] == ["A job"]
    assert business_service.list_own_applicants(a, oa) == []
    try:
        business_service.list_own_applicants(b, oa)
        assert False, "business B must not see business A's job"
    except ValueError as exc:
        assert "not found" in str(exc).lower()


def test_browse_filters_search_location_and_paginate(test_database):
    b1 = business_service.create_business("Filter One", "O", "Retail", "Mochudi", "x")
    b2 = business_service.create_business("Filter Two", "O", "Retail", "Maun", "x")
    opportunity_service.create_opportunity(b1, "Plumbing repair", "pipes", None, 0)
    opportunity_service.create_opportunity(b2, "Website build", "web", None, 0)
    y = create_youth(name="Searcher")
    titles = lambda **kw: sorted(o["title"] for o in opportunity_service.browse_open_opportunities(y, **kw))
    assert titles(q="plumb") == ["Plumbing repair"]
    assert titles(location="maun") == ["Website build"]
    assert len(titles(limit=1)) == 1 and len(titles(limit=1, offset=1)) == 1
    assert titles(q="100%") == []                                     # wildcard characters are not special


def test_public_profile_is_opt_in_and_hides_private_data(test_database):
    y = create_youth(name="Public Person")
    try:
        profile_service.get_public_profile(y)
        assert False, "profiles are private by default"
    except ValueError:
        pass
    profile_service.update_profile(y, {"bio": "Builder", "location": "Gaborone", "public_profile": True})
    p = profile_service.get_public_profile(y)
    assert p["name"] == "Public Person" and p["bio"] == "Builder"
    assert not ({"email", "intake", "revenue", "password_hash"} & set(p))
    profile_service.update_profile(y, {"location": "Gaborone", "public_profile": False})
    try:
        profile_service.get_public_profile(y)
        assert False
    except ValueError:
        pass


def test_notifications_read_state(test_database):
    y = create_youth(name="Notified")
    from app.db.database import transaction
    with transaction() as db:
        notification_service.notify(db, "youth", y, "test", "Hello", "World")
    assert notification_service.list_notifications("youth", y)["unread"] == 1
    notification_service.mark_all_read("youth", y)
    assert notification_service.list_notifications("youth", y)["unread"] == 0
    other = create_youth(name="Other Person")
    assert notification_service.list_notifications("youth", other)["items"] == []


def test_token_roles_do_not_cross():
    from app.services.auth_service import create_access_token, decode_access_token
    ybt = create_access_token("11111111-1111-1111-1111-111111111111", role="business")
    yt = create_access_token("22222222-2222-2222-2222-222222222222")
    assert decode_access_token(ybt, role="youth") is None
    assert decode_access_token(yt, role="business") is None
    assert decode_access_token(ybt, role="business") == "11111111-1111-1111-1111-111111111111"
    assert decode_access_token(yt) == "22222222-2222-2222-2222-222222222222"


def _accepted_job(budget=500, name="Gate Shop"):
    bid = business_service.create_business(name, "Owner", "Retail", "Maun", "x")
    oid = opportunity_service.create_opportunity(bid, "Paint wall", "d", None, budget)
    yid = create_youth(name="W " + name)
    aid = assignment_service.create_assignment(yid, oid, mode="application")
    business_service.accept_applicant(bid, aid)
    return bid, oid, yid, aid


def test_job_cannot_be_completed_without_approved_work(test_database):
    bid, oid, yid, aid = _accepted_job()
    try:
        assignment_service.complete_assignment(aid)
        assert False, "no proof, no completion"
    except ValueError as exc:
        assert "approved" in str(exc)
    assert payment_service.list_invoices(business_id=bid) == []


def test_business_hires_reviews_and_approval_issues_invoice(test_database):
    from app.services import trial_service
    bid, oid, yid, aid = _accepted_job(500, "Flow Shop")
    people = business_service.list_own_applicants(bid, oid)
    assert people[0]["status"] == "Accepted" and people[0]["trial_status"] is None

    trial = trial_service.create_trial(aid)
    trial_service.start_trial(trial)
    trial_service.submit_trial(trial, {"summary": "Painted"})
    assert business_service.list_own_applicants(bid, oid)[0]["trial_status"] == "Submitted"

    business_service.approve_work(bid, trial, 90, "Great")
    assert assignment_service.get_assignment(aid)["status"] == "Completed"
    assert float(payment_service.list_invoices(business_id=bid)[0]["amount"]) == 500.0
    try:
        business_service.approve_work(bid, trial, 90)
        assert False, "already approved"
    except Conflict:
        pass


def test_other_business_cannot_hire_or_approve(test_database):
    from app.services import trial_service
    bid, oid, yid, aid = _accepted_job(100, "Mine Shop")
    other = business_service.create_business("Thief Shop", "O", "Retail", "Maun", "x")
    for call in (lambda: business_service.accept_applicant(other, aid),
                 lambda: business_service.decline_applicant(other, aid),
                 lambda: business_service.close_own_job(other, oid)):
        try:
            call()
            assert False
        except ValueError as exc:
            assert "not found" in str(exc).lower()
    trial = trial_service.create_trial(aid)
    trial_service.start_trial(trial)
    trial_service.submit_trial(trial, {"summary": "x"})
    try:
        business_service.approve_work(other, trial, 100)
        assert False
    except ValueError as exc:
        assert "not found" in str(exc).lower()


def test_business_cannot_accept_a_staff_offer(test_database):
    bid = business_service.create_business("Offer Shop", "O", "Retail", "Maun", "x")
    oid = opportunity_service.create_opportunity(bid, "Offer job", "d", None, 0)
    yid = create_youth(name="Offered")
    aid = assignment_service.create_assignment(yid, oid, mode="offer")
    try:
        business_service.accept_applicant(bid, aid)
        assert False
    except Forbidden:
        pass


def test_cancelled_trial_can_be_restarted(test_database):
    from app.api import service as api
    bid, oid, yid, aid = _accepted_job(0, "Restart Shop")
    first = api.create_my_trial(yid, aid)["id"]
    api.cancel_my_trial(yid, first, "phone broke")
    second = api.create_my_trial(yid, aid)["id"]
    assert second != first
    rows = [r for r in assignment_service.list_youth_assignments(yid) if str(r["assignment_id"]) == str(aid)]
    assert len(rows) == 1 and rows[0]["trial_status"] == "Active"        # one row, latest trial


def test_submitted_link_becomes_trial_evidence(test_database):
    from app.api import service as api
    from app.services import evidence_service
    bid, oid, yid, aid = _accepted_job(0, "Evidence Shop")
    trial = api.create_my_trial(yid, aid)["id"]
    api.submit_my_trial(yid, trial, {"summary": "Built it", "link": "https://example.com/work"})
    assert [e["url"] for e in evidence_service.list_trial_evidence(trial)] == ["https://example.com/work"]


def test_unmatched_provider_money_is_parked_not_lost(test_database):
    import os
    bid, yid, aid, invoice = _completed_job(300, "Park Shop")
    os.environ["BSTM_WEBHOOK_SECRET_SMS_BRIDGE"] = "s3cret-s3cret"
    ev = lambda ref, inv, amt: {"invoice_reference": inv, "provider_ref": ref, "amount": amt, "method": "MyZaka"}

    assert payment_service.record_provider_payment("sms-bridge", ev("UNK-00001", "BSTM-NOPE", 300)) is None
    assert payment_service.record_provider_payment("sms-bridge", ev("OK-000001", invoice["reference"], 300))
    assert payment_service.record_provider_payment("sms-bridge", ev("LATE-0001", invoice["reference"], 300)) is None   # already paid
    assert payment_service.record_provider_payment("sms-bridge", ev("UNK-00001", "BSTM-NOPE", 300)) is None          # retry is harmless

    open_items = payment_service.list_unmatched()
    assert sorted(i["provider_ref"] for i in open_items) == ["LATE-0001", "UNK-00001"]
    assert len(queue_service.review_queue()["unmatched"]) == 2
    payment_service.resolve_unmatched(open_items[0]["id"], "Refunded customer")
    assert len(payment_service.list_unmatched()) == 1


def test_migration_runner_tracks_and_is_rerunnable(test_database):
    from app.services import migration_service
    st = migration_service.status()
    assert all(n < migration_service.BASELINE_CUTOFF for n in st["applied"])      # older ones assumed applied
    assert len(st["pending"]) >= 3 and "20261016000000_ledger_notifications_accounts.sql" in st["pending"]
    first = migration_service.apply_pending()                                       # files are idempotent: re-running over an up-to-date schema is safe
    assert first["pending"] == [] and len(first["applied_now"]) >= 3
    assert migration_service.apply_pending()["applied_now"] == []                  # nothing left
