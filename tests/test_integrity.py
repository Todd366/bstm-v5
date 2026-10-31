"""Cross-cutting rules: deleted people, money rounding, void then re-issue, races."""
import threading
from decimal import Decimal

import pytest

from app.core.errors import Conflict
from app.services import (agent_service, assignment_service, business_service, capability_service, matching_service,
                          opportunity_service, payment_service, privacy_service, profile_service, youth_service)
from tests.helpers import create_youth, finish_work
from tests.test_ledger_flows import _completed_job
from tests.test_concurrency import _race

PW = "correct-horse-battery"


def test_deleted_person_vanishes_everywhere_and_phone_is_freed(test_database):
    web = capability_service.create_capability("Web Dev", "Technology")
    r = agent_service.register_person("ak", "Mpho", "Gone Person", "78123456", "Maun", None, True)
    yid = r["id"]
    capability_service.assign_capability_to_youth(yid, web, "Advanced")
    bid = business_service.create_business("Gone Shop", "O", "Retail", "Maun", "x", email="goneshop@example.com", password=PW)
    oid = opportunity_service.create_opportunity(bid, "Site", "d", None, 100, skills=[web])
    assert [c["name"] for c in matching_service.candidates_for_opportunity(oid)] == ["Gone Person"]

    youth_service.change_password(yid, r["temporary_password"], "my-own-password-1")
    privacy_service.delete_youth(yid, "my-own-password-1")

    assert matching_service.candidates_for_opportunity(oid) == []
    assert all(y["id"] != yid for y in youth_service.list_youth())
    assert agent_service.my_people("ak") == []
    with pytest.raises(ValueError):
        profile_service.get_public_profile(yid)
    row = youth_service.get_youth(yid)
    assert row["phone"] is None and row["email"] is None
    again = youth_service.create_youth("New Owner", "Maun", "Work", None, PW, phone="78123456")   # number can be reused
    assert again != yid


def test_money_split_always_adds_up_to_the_cent(test_database):
    for i, budget in enumerate([333.33, 0.05, 1234.57, 99.99, 10]):
        bid = business_service.create_business("Round Shop %d" % i, "O", "Retail", "Maun", "x", email="round%d@example.com" % i, password=PW)
        oid = opportunity_service.create_opportunity(bid, "Job", "d", None, budget)
        yid = create_youth(name="Round %d" % i)
        aid = assignment_service.create_assignment(yid, oid, mode="application")
        assignment_service.accept_assignment(aid)
        finish_work(aid)
        inv = payment_service.list_invoices(business_id=bid)[0]
        assert Decimal(str(inv["youth_share"])) + Decimal(str(inv["platform_share"])) == Decimal(str(inv["amount"])) == Decimal(str(budget)).quantize(Decimal("0.01"))


def test_void_then_reissue_corrected_invoice_once(test_database):
    bid, yid, aid, inv = _completed_job(1000, "Reissue Shop")
    with pytest.raises(Conflict):
        payment_service.reissue_invoice(inv["id"], 800)           # still live: not allowed
    payment_service.void_invoice(inv["id"], "wrong amount")
    listed = {i["id"]: i for i in payment_service.list_invoices(business_id=bid)}
    assert listed[inv["id"]]["can_reissue"] is True
    new_id = payment_service.reissue_invoice(inv["id"], 800)
    new = [i for i in payment_service.list_invoices(business_id=bid) if i["id"] == new_id][0]
    assert new["status"] == "Issued" and float(new["amount"]) == 800.0 and float(new["youth_share"]) == 560.0
    with pytest.raises(Conflict):
        payment_service.reissue_invoice(inv["id"], 900)            # only one live invoice per job
    assert [i for i in payment_service.list_invoices(business_id=bid) if i["id"] == inv["id"]][0]["can_reissue"] is False


def test_business_accepting_while_person_withdraws_ends_in_one_state(test_database):
    bid = business_service.create_business("Race Accept", "O", "Retail", "Maun", "x", email="raceaccept@example.com", password=PW)
    oid = opportunity_service.create_opportunity(bid, "Job", "d", None, 100)
    yid = create_youth(name="Racer")
    aid = assignment_service.create_assignment(yid, oid, mode="application")
    ok, errs = _race([lambda: assignment_service.accept_assignment(aid), lambda: assignment_service.cancel_assignment(aid, acting_youth_id=yid)])
    final = assignment_service.get_assignment(aid)["status"]
    assert final in ("Accepted", "Cancelled") and len(ok) + len(errs) == 2 and len(ok) >= 1
