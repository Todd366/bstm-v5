"""Staff accounts and roles, password reset codes, invoice void, data
export and account deletion, system check."""

import asyncio
import json

import pytest

from app.core import middleware as mw
from app.core.errors import Conflict, Forbidden
from app.services import (
    business_service,
    payment_service,
    privacy_service,
    reset_service,
    scorecard_service,
    staff_service,
)
from app.services.auth_service import create_access_token, verify_password
from app.db.database import transaction
from tests.helpers import create_youth
from tests.test_ledger_flows import _completed_job
from tests.test_middleware import call, bearer

PW = "correct-horse-battery"


def _staff(role, email=None):
    sid = staff_service.create_staff("Tau " + role, email or role + "@bstm.test", PW, role)
    return sid, create_access_token(sid, role="staff")


def test_staff_login_and_role_matrix(test_database):
    fin_id, fin = _staff("finance")
    _, field = _staff("field")
    _, sup = _staff("support")
    _, adm = _staff("admin")

    s = staff_service.authenticate_staff("finance@bstm.test", PW)
    assert s["role"] == "finance"
    with pytest.raises(ValueError):
        staff_service.authenticate_staff("finance@bstm.test", "wrong-password-x")
    with pytest.raises(ValueError):
        staff_service.authenticate_staff("nobody@bstm.test", PW)

    matrix = {
        ("GET", "/invoices"): (fin, adm),
        ("POST", "/payments/x/confirm"): (fin, adm),
        ("GET", "/opportunities"): (field, adm),
        ("POST", "/opportunities/x/approval"): (field, adm),
        ("GET", "/youth"): (field, sup, adm),
        ("POST", "/admin/resets"): (sup, adm),
        ("GET", "/admin/queue"): (fin, field, sup, adm),
        ("GET", "/admin/staff"): (),
        ("GET", "/admin/owner/records"): (),
        ("POST", "/admin/migrations/apply"): (adm,),
    }
    everyone = {"fin": fin, "field": field, "sup": sup, "adm": adm}
    for (method, path), allowed in matrix.items():
        for name, tok in everyone.items():
            status = call(method, path, bearer(tok))[0]
            assert status == (200 if tok in allowed else 403), (method, path, name, status)

    # other kinds of token never work on staff routes
    assert call("GET", "/invoices", bearer(create_access_token("11111111-1111-1111-1111-111111111111")))[0] == 401
    # only the owner (by email) and the shared key reach owner tools
    from app.core.config import OWNER_EMAIL
    _, owner = _staff("admin", OWNER_EMAIL)
    assert call("GET", "/admin/staff", bearer(owner))[0] == 200
    assert call("GET", "/admin/owner/records", bearer(owner))[0] == 200
    assert call("GET", "/invoices", bearer(owner))[0] == 200
    # the shared key still works as admin
    status, out = call("GET", "/admin/staff", {"X-API-Key": mw.API_KEY})
    assert status == 200 and json.loads(out["body"])["is_admin"] is True

    # deactivation takes effect immediately
    staff_service.set_staff_active(fin_id, False)
    assert call("GET", "/invoices", bearer(fin))[0] == 401


def test_cannot_remove_last_admin_or_self(test_database):
    a, _ = _staff("admin")
    with pytest.raises(Conflict):
        staff_service.set_staff_active(a, False)
    b, _ = _staff("admin", "admin2@bstm.test")
    with pytest.raises(ValueError):
        staff_service.set_staff_active(b, False, acting_id=b)
    staff_service.set_staff_active(a, False)


def test_duplicate_staff_email_and_bad_role(test_database):
    _staff("field")
    with pytest.raises(Conflict):
        _staff("field")
    with pytest.raises(ValueError):
        staff_service.create_staff("X", "x@bstm.test", PW, "king")


def test_reset_code_flow(test_database):
    create_youth(name="Reset Person", email="reset@example.com")
    with pytest.raises(ValueError):
        reset_service.create_reset_code("youth", "unknown@example.com")

    code = reset_service.create_reset_code("youth", "reset@example.com")["code"]

    for _ in range(3):
        with pytest.raises(Forbidden):
            reset_service.redeem_reset_code("youth", "reset@example.com", "WRONGCODE", "new-password-123")

    reset_service.redeem_reset_code("youth", "reset@example.com", code.lower(), "new-password-123")

    with transaction() as db:
        h = db.execute("SELECT password_hash FROM youth WHERE email = 'reset@example.com'").fetchone()["password_hash"]
    assert verify_password("new-password-123", h)

    with pytest.raises(Forbidden):   # single use
        reset_service.redeem_reset_code("youth", "reset@example.com", code, "another-password-1")


def test_reset_locks_after_five_wrong_guesses_and_newest_code_wins(test_database):
    create_youth(name="Lock Person", email="lock@example.com")
    old = reset_service.create_reset_code("youth", "lock@example.com")["code"]
    new = reset_service.create_reset_code("youth", "lock@example.com")["code"]
    with pytest.raises(Forbidden):
        reset_service.redeem_reset_code("youth", "lock@example.com", old, "new-password-123")

    # the wrong guesses persisted, so the 5th wrong attempt locks even the right code out
    for _ in range(4):
        with pytest.raises(Forbidden):
            reset_service.redeem_reset_code("youth", "lock@example.com", "WRONGCODE", "new-password-123")
    with pytest.raises(Forbidden):
        reset_service.redeem_reset_code("youth", "lock@example.com", new, "new-password-123")


def test_business_reset_and_open_list(test_database):
    business_service.create_business("Reset Biz", "Owner", "Retail", "Maun", "x", email="rb@example.com", password=PW)
    code = reset_service.create_reset_code("business", "rb@example.com")["code"]
    assert len(reset_service.list_open_resets()) == 1
    reset_service.redeem_reset_code("business", "rb@example.com", code, "brand-new-pass-1")
    assert business_service.authenticate_business("rb@example.com", "brand-new-pass-1")
    assert reset_service.list_open_resets() == []


def test_void_invoice_rules(test_database):
    _completed_job(name="Void Shop")
    invoice = payment_service.list_invoices()[0]
    pid = payment_service.submit_payment(invoice["id"], "OrangeMoney", provider_ref="OM-REF-0001", business_id=invoice["business_id"])
    with pytest.raises(Conflict):
        payment_service.void_invoice(invoice["id"], "mistake")
    payment_service.reject_payment(pid, "bad")
    payment_service.void_invoice(invoice["id"], "Wrong amount", voided_by="Tau")
    with pytest.raises(Conflict):
        payment_service.void_invoice(invoice["id"], "again")
    assert payment_service.list_invoices(status="Void")


def test_export_and_delete_account(test_database):
    yid = create_youth(name="Leaver", email="leaver@example.com", password=PW)
    data = privacy_service.export_youth(yid)
    assert data["profile"]["email"] == "leaver@example.com" and "password_hash" not in data["profile"]

    with pytest.raises(Forbidden):
        privacy_service.delete_youth(yid, "not-my-password-1")
    assert privacy_service.delete_youth(yid, PW)["status"] == "deleted"

    with transaction() as db:
        row = db.execute("SELECT name, email, password_hash, deleted_at FROM youth WHERE id = ?", (yid,)).fetchone()
    assert row["name"] == "Deleted member" and row["email"] is None and row["password_hash"] is None and row["deleted_at"]
    with pytest.raises(ValueError):
        privacy_service.delete_youth(yid, PW)


def test_scorecard_reports_real_state(test_database):
    card = scorecard_service.scorecard()
    names = {c["name"]: c for c in card["checks"]}
    assert card["overall"] in ("OK", "WARN", "FAIL")
    assert names["Ledger balance"]["status"] == "OK"
    assert names["Named admin accounts"]["status"] == "WARN"
    _staff("admin")
    assert {c["name"]: c for c in scorecard_service.scorecard()["checks"]}["Named admin accounts"]["status"] == "OK"


def test_owner_can_edit_and_delete_but_money_is_protected(test_database):
    from app.services import opportunity_service, owner_service

    yid = create_youth(name="Test Person", email="t1@example.com")
    real = create_youth(name="Real Person", email="real@gmail.com")
    rows = {r["name"]: r for r in owner_service.list_records("youth")}
    assert rows["Test Person"]["suggested_test"] and not rows["Real Person"]["suggested_test"]

    owner_service.update_record("youth", real, {"location": "Maun", "goal": "Farm"}, actor="Owner")
    with transaction() as db:
        assert db.execute("SELECT location FROM youth WHERE id = ?", (real,)).fetchone()["location"] == "Maun"
    with pytest.raises(ValueError):
        owner_service.update_record("youth", real, {}, actor="Owner")

    with pytest.raises(ValueError):
        owner_service.delete_records("youth", [yid], "yes")
    res = owner_service.delete_records("youth", [yid], "DELETE", actor="Owner")
    assert res["removed"] == [yid] and len(owner_service.list_records("youth")) == 1

    # a business with a paid job history cannot be deleted
    _completed_job(name="Money Shop")
    biz = [r for r in owner_service.list_records("businesses") if r["name"] == "Money Shop"][0]
    res = owner_service.delete_records("businesses", [str(biz["id"])], "DELETE")
    assert res["removed"] == [] and res["kept_because_of_money"]

    # a business with only jobs: both go
    b2 = business_service.create_business("Plain Shop", "Owner", "Retail", "Maun", "x", email="plain@example.com", password=PW)
    opportunity_service.create_opportunity(b2, "Paint", "d", None, 100)
    res = owner_service.delete_records("businesses", [b2], "DELETE")
    assert res["removed"] == [b2]
    with transaction() as db:
        assert db.execute("SELECT count(*) AS n FROM opportunities WHERE title = 'Paint'").fetchone()["n"] == 0
