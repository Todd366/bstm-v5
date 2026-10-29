"""The app watches itself, and the lifecycle keeps its promises."""

import pytest

from app.core.errors import Conflict
from app.db.database import transaction
from app.services import attention_service, payment_service, staff_service
from tests.helpers import create_youth
from tests.test_ledger_flows import _completed_job
from tests.test_middleware import bearer, call
from app.services.auth_service import create_access_token

PW = "correct-horse-battery"


def _titles(role="owner"):
    return {i["title"]: i for i in attention_service.attention_for(role)["items"]}


def test_clean_system_is_all_clear(test_database):
    assert attention_service.attention_for("owner")["all_clear"]


def test_full_lifecycle_never_trips_a_fail_invariant(test_database):
    _completed_job(name="Invariant Shop")
    inv = payment_service.list_invoices()[0]
    pid = payment_service.submit_payment(inv["id"], "OrangeMoney", provider_ref="OM-INV-0001", business_id=inv["business_id"])
    payment_service.confirm_payment(pid, "tester")
    po = payment_service.list_payouts()[0]
    payment_service.set_payout_account(po["youth_id"], "OrangeMoney", "Worker Name", "71234567")
    payment_service.mark_payout_paid(po["id"], "OM-PAYOUT-1", paid_by="tester")

    items = attention_service.attention_for("owner")["items"]
    assert [i for i in items if i["level"] == "fail"] == []
    with transaction() as db:
        row = db.execute("SELECT amount, youth_share, platform_share FROM invoices").fetchone()
        assert abs(float(row["youth_share"]) + float(row["platform_share"]) - float(row["amount"])) < 0.01
        assert float(db.execute("SELECT revenue FROM youth").fetchone()["revenue"]) == float(row["youth_share"])


def test_waiting_items_are_reported_by_area(test_database):
    _completed_job(name="Waiting Shop")
    inv = payment_service.list_invoices()[0]
    payment_service.submit_payment(inv["id"], "OrangeMoney", provider_ref="OM-WAIT-0001", business_id=inv["business_id"])

    assert "Payments to confirm" in _titles("finance")
    assert "Payments to confirm" in _titles("owner")
    assert "Payments to confirm" not in _titles("field")
    assert "Payments to confirm" not in _titles("support")


def test_broken_ledger_is_caught_as_fail(test_database):
    _completed_job(name="Broken Shop")
    with transaction() as db:
        db.execute("UPDATE invoices SET platform_share = platform_share + 50")
    t = _titles("owner")
    assert t["Invoice split does not add up"]["level"] == "fail"
    assert attention_service.attention_for("owner")["all_clear"] is False


def test_old_records_with_no_login_are_flagged(test_database):
    yid = create_youth(name="Old Record")
    with transaction() as db:
        db.execute("UPDATE youth SET password_hash = NULL, email = NULL WHERE id = ?", (yid,))
    assert "People who cannot log in" in _titles("owner")
    assert "People who cannot log in" in _titles("support")
    assert "People who cannot log in" not in _titles("finance")


def test_owner_can_promote_and_demote_team(test_database):
    sid = staff_service.create_staff("Pro Mote", "promote@bstm.test", PW, "support")
    assert staff_service.set_staff_role(sid, "finance")["from"] == "support"
    assert staff_service.authenticate_staff("promote@bstm.test", PW)["role"] == "finance"
    with pytest.raises(ValueError):
        staff_service.set_staff_role(sid, "finance")
    with pytest.raises(ValueError):
        staff_service.set_staff_role(sid, "emperor")
    pending = staff_service.signup_staff("Wait Er", "wait@bstm.test", PW)
    with pytest.raises(Conflict):
        staff_service.set_staff_role(pending, "admin")

    # a promoted person's very next request uses the new role
    tok = create_access_token(sid, role="staff")
    assert call("GET", "/invoices", bearer(tok))[0] == 200
    staff_service.set_staff_role(sid, "support")
    assert call("GET", "/invoices", bearer(tok))[0] == 403


def test_support_and_finance_do_not_see_private_intake(test_database):
    from app.api.service import youth_profile_for_staff

    yid = create_youth(name="Private Person", intake={"interests": ["Technology"], "challenges": ["No network"]})
    assert "intake" in youth_profile_for_staff(yid, "owner")
    assert "intake" in youth_profile_for_staff(yid, "field")
    assert "intake" not in youth_profile_for_staff(yid, "support")
    assert "intake" not in youth_profile_for_staff(yid, "finance")
