"""End-to-end service flows: applications vs offers, ownership,
self-service trials, matching, registration, auth. Needs the database
fixture (a throw-away schema; see conftest.py)."""

import pytest

from app.api import service as api
from app.core.errors import Conflict, Forbidden, RateLimitExceeded
from app.db.database import transaction
from app.services.assignment_service import (
    accept_assignment,
    cancel_assignment,
    complete_assignment,
    create_assignment,
    decline_assignment,
    list_youth_assignments,
)
from app.services.auth_service import hash_password
from app.services.business_service import create_business
from app.services.capability_service import (
    assign_capability_to_youth,
    create_capability,
)
from app.services.evidence_service import submit_evidence
from app.services.matching_service import match_youth_to_opportunities
from app.services.opportunity_service import create_opportunity, get_opportunity
from app.services.trial_service import get_trial
from app.services.youth_service import authenticate_youth, get_youth
from tests.helpers import create_youth


def _business(name="Shop", location="Mochudi"):
    return create_business(
        name=name, owner="Owner", sector="Retail",
        location=location, main_problem="Needs help",
    )


def _opportunity(title="Build a website", **kw):
    return create_opportunity(business_id=_business(name=f"B-{title}"), title=title, **kw)


def _status(opportunity_id):
    return get_opportunity(opportunity_id)["status"]


# ---------- registration ----------

def test_two_people_can_share_a_name(test_database):
    a = create_youth(name="Thabo Mokoena")
    b = create_youth(name="Thabo Mokoena")
    assert a != b


def test_duplicate_email_is_a_conflict(test_database):
    create_youth(name="A", email="same@example.com")
    with pytest.raises(Conflict):
        create_youth(name="B", email="same@example.com")


def test_registration_claims_catalog_capabilities(test_database):
    cap = create_capability("Web Development", "Technology")
    youth_id = create_youth(
        name="Skilled", capabilities=[{"capability_id": cap, "level": "Advanced"}]
    )
    claimed = api.get_my_capabilities(youth_id)
    assert len(claimed) == 1 and claimed[0]["level"] == "Advanced"
    assert claimed[0]["verified"] is False


def test_registration_rejects_bad_capability_id(test_database):
    with pytest.raises(ValueError, match="not found"):
        create_youth(name="X", capabilities=[{"capability_id": "nope"}])


def test_activate_youth_returns_a_token(test_database):
    result = api.activate_youth({
        "name": "Token Person", "location": "Maun", "goal": "Learn",
        "email": "token@example.com", "password": "long-enough-pw",
    })
    assert result["access_token"] and result["id"]


def test_profile_never_contains_password_hash(test_database):
    youth_id = create_youth(name="Private")
    assert "password_hash" not in get_youth(youth_id)
    assert all("password_hash" not in y for y in api.list_youth())


def test_non_uuid_ids_are_not_found_not_a_crash(test_database):
    with pytest.raises(ValueError, match="not found"):
        get_youth("abc")
    with pytest.raises(ValueError, match="not found"):
        get_trial("123")


# ---------- auth ----------

def test_login_success_and_uniform_failure(test_database):
    create_youth(name="Login", email="login@example.com", password="right-password")
    assert authenticate_youth("LOGIN@example.com", "right-password")

    with pytest.raises(ValueError) as wrong:
        authenticate_youth("login@example.com", "wrong-password")
    with pytest.raises(ValueError) as unknown:
        authenticate_youth("nobody@example.com", "wrong-password")
    assert str(wrong.value) == str(unknown.value) == "Invalid email or password"


def test_account_login_attempts_are_throttled(test_database):
    create_youth(name="Throttle", email="t@example.com", password="right-password")
    for _ in range(8):
        with pytest.raises(ValueError):
            authenticate_youth("t@example.com", "wrong-password")
    with pytest.raises(RateLimitExceeded):
        authenticate_youth("t@example.com", "right-password")


def test_old_password_hash_is_upgraded_at_login(test_database):
    youth_id = create_youth(name="Old", email="old@example.com", password="right-password")
    with transaction() as db:
        db.execute(
            "UPDATE youth SET password_hash = ? WHERE id = ?",
            (hash_password("right-password", iterations=1000), youth_id),
        )
    assert authenticate_youth("old@example.com", "right-password") == youth_id
    with transaction() as db:
        stored = db.execute(
            "SELECT password_hash FROM youth WHERE id = ?", (youth_id,)
        ).fetchone()["password_hash"]
    assert stored.split("$")[1] != "1000"


# ---------- opportunities ----------

def test_budget_and_department_are_saved(test_database):
    result = api.create_business_opportunity({
        "business_id": _business(), "title": "Run our socials",
        "department": "Social Media Management", "budget": 800,
    })
    saved = get_opportunity(result["id"])
    assert float(saved["budget"]) == 800
    assert saved["department"] == "Social Media Management"


# ---------- applications vs offers ----------

def test_applying_does_not_lock_the_opportunity(test_database):
    opp = _opportunity()
    a, b = create_youth(name="A"), create_youth(name="B")
    api.apply_to_opportunity(a, opp)
    api.apply_to_opportunity(b, opp)
    assert _status(opp) == "Open"


def test_cannot_apply_twice(test_database):
    opp = _opportunity()
    a = create_youth(name="A")
    api.apply_to_opportunity(a, opp)
    with pytest.raises(Conflict, match="already applied"):
        api.apply_to_opportunity(a, opp)


def test_open_application_cap(test_database):
    a = create_youth(name="Busy")
    for i in range(5):
        api.apply_to_opportunity(a, _opportunity(f"Job {i}"))
    with pytest.raises(Conflict, match="at most 5"):
        api.apply_to_opportunity(a, _opportunity("One too many"))


def test_admin_accepting_one_applicant_declines_the_rest(test_database):
    opp = _opportunity()
    a, b = create_youth(name="A"), create_youth(name="B")
    first = api.apply_to_opportunity(a, opp)["assignment_id"]
    api.apply_to_opportunity(b, opp)

    accept_assignment(first)

    assert _status(opp) == "InProgress"
    statuses = {r["opportunity_id"]: r["status"] for r in list_youth_assignments(b)}
    assert statuses[opp] == "Declined"


def test_youth_cannot_accept_their_own_application(test_database):
    opp = _opportunity()
    a = create_youth(name="A")
    assignment = api.apply_to_opportunity(a, opp)["assignment_id"]
    with pytest.raises(Forbidden):
        api.accept_my_assignment(a, assignment)


def test_direct_offer_locks_and_youth_can_accept(test_database):
    opp = _opportunity()
    a, b = create_youth(name="A"), create_youth(name="B")
    api.apply_to_opportunity(b, opp)

    offer = create_assignment(a, opp, mode="offer")
    assert _status(opp) == "Assigned"
    # B's pending application was closed by the offer.
    assert list_youth_assignments(b)[0]["status"] == "Declined"

    api.accept_my_assignment(a, offer)
    assert _status(opp) == "InProgress"


def test_declined_offer_reopens(test_database):
    opp = _opportunity()
    a = create_youth(name="A")
    offer = create_assignment(a, opp, mode="offer")
    api.decline_my_assignment(a, offer)
    assert _status(opp) == "Open"


def test_ownership_is_enforced(test_database):
    opp = _opportunity()
    a, b = create_youth(name="A"), create_youth(name="B")
    offer = create_assignment(a, opp, mode="offer")
    with pytest.raises(ValueError, match="not found"):
        api.accept_my_assignment(b, offer)
    with pytest.raises(ValueError, match="not found"):
        api.withdraw_my_assignment(b, offer)


def test_second_offer_for_a_taken_opportunity_is_refused(test_database):
    opp = _opportunity()
    a, b = create_youth(name="A"), create_youth(name="B")
    create_assignment(a, opp, mode="offer")
    with pytest.raises(Conflict, match="not open"):
        create_assignment(b, opp, mode="offer")


# ---------- self-service trial lifecycle ----------

def _accepted(youth_id, opp):
    assignment = create_assignment(youth_id, opp, mode="offer")
    accept_assignment(assignment)
    return assignment


def test_self_service_trial_lifecycle(test_database):
    opp = _opportunity()
    a, b = create_youth(name="A"), create_youth(name="B")
    assignment = _accepted(a, opp)

    trial = api.create_my_trial(a, assignment)
    assert trial["status"] == "active"

    with pytest.raises(ValueError, match="not found"):
        api.submit_my_trial(b, trial["id"], {"summary": "not mine"})

    api.submit_my_trial(a, trial["id"], {"summary": "done"})
    assert api.get_my_trial(a, trial["id"])["status"] == "Submitted"


def test_withdrawing_cancels_trial_with_penalty_and_reopens(test_database):
    opp = _opportunity()
    a = create_youth(name="A")
    assignment = _accepted(a, opp)
    trial = api.create_my_trial(a, assignment)
    before = float(get_youth(a)["reliability_score"])

    api.withdraw_my_assignment(a, assignment)

    assert api.get_my_trial(a, trial["id"])["status"] == "Cancelled"
    assert float(get_youth(a)["reliability_score"]) < before
    assert _status(opp) == "Open"


def test_completion_pays_the_youth_share(test_database):
    opp = _opportunity(budget=100)
    a = create_youth(name="A")
    assignment = _accepted(a, opp)
    complete_assignment(assignment)
    assert float(get_youth(a)["revenue"]) == 70.0


# ---------- evidence ----------

def test_evidence_links_must_be_http(test_database):
    a = create_youth(name="A")
    with pytest.raises(ValueError, match="http"):
        submit_evidence(a, "Portfolio", url="javascript:alert(1)")
    assert submit_evidence(a, "Portfolio", url="https://example.com/work")


def test_self_evidence_is_attached_to_the_caller(test_database):
    a = create_youth(name="A")
    api.submit_my_evidence(a, {"kind": "Document", "notes": "certificate"})
    assert len(api.get_my_evidence(a)) == 1


# ---------- matching ----------

def test_short_capability_names_do_not_match_inside_words(test_database):
    a = create_youth(name="A")
    ai = create_capability("AI", "Technology")
    assign_capability_to_youth(a, ai)
    _opportunity("Retail shop email campaign")
    assert match_youth_to_opportunities(a) == []


def test_matching_returns_one_row_per_opportunity_best_first(test_database):
    a = create_youth(name="A", location="Mochudi")
    web = create_capability("Web Development", "Technology")
    design = create_capability("Graphic Design", "Creative")
    assign_capability_to_youth(a, web, "Advanced")
    assign_capability_to_youth(a, design, "Beginner")

    both = create_opportunity(
        business_id=_business(name="Both", location="Mochudi"),
        title="Web Development and Graphic Design for our shop",
    )
    create_opportunity(
        business_id=_business(name="OnlyWeb", location="Maun"),
        title="Web Development",
    )

    matches = match_youth_to_opportunities(a)
    assert [m["opportunity_id"] for m in matches].count(both) == 1
    assert matches[0]["opportunity_id"] == both
    assert "In your area" in matches[0]["reasons"]
    assert len(matches[0]["matched_capabilities"]) == 2


def test_applied_opportunities_leave_the_match_list(test_database):
    a = create_youth(name="A")
    web = create_capability("Web Development", "Technology")
    assign_capability_to_youth(a, web)
    opp = _opportunity("Web Development")
    assert len(match_youth_to_opportunities(a)) == 1
    api.apply_to_opportunity(a, opp)
    assert match_youth_to_opportunities(a) == []


# ---------- operations: brief, diagnosis, audits, queue ----------

def test_brief_recommends_department_from_intake():
    from app.services.brief_service import build_brief

    brief = build_brief({"interests": ["Technology"], "resources": ["Smartphone", "Computer"], "availability": "Full-time"})
    assert brief["primary"]["name"]
    assert brief["primary"]["score"] > 0
    assert len(brief["alternatives"]) == 3
    assert brief["learning_path"]


def test_brief_handles_empty_intake():
    from app.services.brief_service import build_brief

    assert build_brief(None)["primary"]["name"]


def test_diagnosis_matches_rules_and_has_fallback():
    from app.services.diagnosis_service import diagnose

    names = {f["department"] for f in diagnose("We have no website and no records of money", "Shop")}
    assert "Web Development" in names and "Finance & Accounting" in names
    assert diagnose("???", "Shop")[0]["department"] == "Research & Development"


def test_field_audit_roundtrip_and_validation(test_database):
    from app.services import audit_service, business_service

    bid = business_service.create_business("Audit Shop", "Owner", "Retail", "Mochudi", "No website")
    aid = audit_service.create_field_audit(
        {"business_id": bid, "business_name": "Audit Shop", "location": "Mochudi",
         "ratings": {"Customer traffic": "G", "Bogus": "G"}, "rooms": [3, 1, 3], "score": 7}
    )
    rows = audit_service.list_field_audits()
    assert str(rows[0]["id"]) == aid
    rooms = rows[0]["rooms"]
    if isinstance(rooms, str):  # minimal test driver returns the raw array text
        rooms = [int(x) for x in rooms.strip("{}").split(",") if x]
    assert rooms == [1, 3]
    assert "Bogus" not in rows[0]["ratings"]
    assert business_service.get_business(bid)["audit_status"] == "Completed"

    for bad in ({"rooms": [64]}, {"score": 11}):
        data = {"business_name": "X", "location": "Y", "score": 5}
        data.update(bad)
        try:
            audit_service.create_field_audit(data)
            assert False, "should reject"
        except ValueError:
            pass


def test_review_queue_lists_pending_and_submitted(test_database):
    from app.services import assignment_service, opportunity_service, queue_service, business_service
    from tests.helpers import create_youth

    yid = create_youth(name="Queue Tester")
    bid = business_service.create_business("Queue Shop", "Owner", "Retail", "Maun", "x")
    oid = opportunity_service.create_opportunity(bid, "Fix site", "d", None, 100)
    assignment_service.create_assignment(yid, oid, mode="application")
    queue = queue_service.review_queue()
    assert len(queue["applications"]) == 1 and queue["trials"] == []


def test_close_opportunity_declines_applicants_and_blocks_active_jobs(test_database):
    from app.services import assignment_service, business_service, opportunity_service
    from tests.helpers import create_youth

    bid = business_service.create_business("Close Shop", "Owner", "Retail", "Maun", "x")
    oid = opportunity_service.create_opportunity(bid, "Close me", "d", None, 0)
    yid = create_youth(name="Closer")
    aid = assignment_service.create_assignment(yid, oid, mode="application")

    assert opportunity_service.close_opportunity(oid)["status"] == "Cancelled"
    assert assignment_service.get_assignment(aid)["status"] == "Declined"

    oid2 = opportunity_service.create_opportunity(bid, "Busy job", "d", None, 0)
    aid2 = assignment_service.create_assignment(yid, oid2, mode="application")
    assignment_service.accept_assignment(aid2)
    try:
        opportunity_service.close_opportunity(oid2)
        assert False, "should refuse"
    except ValueError:
        pass


def test_candidates_for_opportunity_ranks_matching_youth(test_database):
    from app.services import business_service, capability_service, matching_service, opportunity_service
    from tests.helpers import create_youth

    bid = business_service.create_business("Cand Shop", "Owner", "Retail", "Mochudi", "x")
    oid = opportunity_service.create_opportunity(bid, "Plumbing repair", "Fix pipes", None, 0)
    cap = capability_service.create_capability("Plumbing", "Trades")
    cap_id = cap if isinstance(cap, str) else cap["id"]
    good = create_youth(name="Plumber", location="Mochudi")
    other = create_youth(name="Nobody")
    capability_service.assign_capability_to_youth(good, cap_id, "Advanced")

    names = [c["name"] for c in matching_service.candidates_for_opportunity(oid)]
    assert names == ["Plumber"] and "Nobody" not in names
