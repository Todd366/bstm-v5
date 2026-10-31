"""Field agents register people; people choose their own password."""
import pytest
from app.core.permissions import is_allowed
from app.services import agent_service, staff_service, youth_service
from app.services.youth_service import authenticate_youth

AGENT = "agent-key-1"


def test_agent_registers_person_with_temp_password(test_database):
    with pytest.raises(ValueError):
        agent_service.register_person(AGENT, "Mpho", "Lesego K", "72345678", "Gumare", None, False)
    r = agent_service.register_person(AGENT, "Mpho", "Lesego K", "72345678", "Gumare", None, True)
    assert authenticate_youth("72345678", r["temporary_password"]) == r["id"]
    assert youth_service.get_youth(r["id"])["must_change_password"] is True
    mine = agent_service.my_people(AGENT)
    assert [p["name"] for p in mine] == ["Lesego K"] and agent_service.my_people("someone-else") == []
    assert len(agent_service.my_people()) >= 1


def test_person_changes_own_password_and_flag_clears(test_database):
    r = agent_service.register_person(AGENT, "Mpho", "Tumi B", "73456789", "Shakawe", "Farming", True)
    with pytest.raises(ValueError):
        youth_service.change_password(r["id"], "wrong-current", "my-own-password-1")
    youth_service.change_password(r["id"], r["temporary_password"], "my-own-password-1")
    assert authenticate_youth("73456789", "my-own-password-1") == r["id"]
    assert youth_service.get_youth(r["id"])["must_change_password"] is False
    with pytest.raises(ValueError):
        authenticate_youth("73456789", r["temporary_password"])


def test_agent_role_is_limited_to_agent_routes(test_database):
    assert is_allowed("agent", "POST", "/admin/agent/register") and is_allowed("agent", "GET", "/admin/me")
    for path in ("/admin/queue", "/youth", "/invoices", "/admin/attention", "/admin/report", "/admin/resets"):
        assert not is_allowed("agent", "GET", path), path
    assert not is_allowed("finance", "POST", "/admin/agent/register")
    sid = staff_service.create_staff("Agent A", "agent@bstm.test", "a-long-password-12", "agent")
    assert sid


def test_agent_helps_only_people_they_registered(test_database):
    from app.services import business_service, opportunity_service
    from tests.helpers import create_youth
    mine = agent_service.register_person(AGENT, "Mpho", "Neo M", "74561234", "Maun", None, True)["id"]
    other = agent_service.register_person("agent-key-2", "Kabo", "Ona P", "75671234", "Maun", None, True)["id"]
    self_signed = create_youth(name="Self Signed")
    bid = business_service.create_business("Agent Shop", "Owner", "Retail", "Maun", "x", email="agentshop@example.com", password="correct-horse-battery")
    oid = opportunity_service.create_opportunity(bid, "Paint sign", "Needs paint", None, 100)

    agent_service.person_apply(AGENT, "Mpho", mine, oid)
    work = agent_service.person_work(AGENT, mine)
    assert [w["opportunity_title"] for w in work] == ["Paint sign"]
    agent_service.person_evidence(AGENT, "Mpho", mine, {"kind": "Other", "notes": "Photo of earlier sign"})

    for victim in (other, self_signed):
        with pytest.raises(ValueError):
            agent_service.person_apply(AGENT, "Mpho", victim, oid)
        with pytest.raises(ValueError):
            agent_service.person_work(AGENT, victim)
    # admins (agent_key None) may help any agent-registered person, but not a self-signed one
    assert agent_service.person_work(None, other) == []
    with pytest.raises(ValueError):
        agent_service.person_work(None, self_signed)


def test_agent_starts_work_and_submits_field_card_for_person(test_database):
    from app.services import assignment_service, business_service, opportunity_service
    from tests.test_field_card import GOOD
    pid = agent_service.register_person(AGENT, "Mpho", "Field Person", "75123456", "Maun", None, True)["id"]
    other = agent_service.register_person("agent-key-3", "Kabo", "Other Person", "76123457", "Maun", None, True)["id"]
    bid = business_service.create_business("Card Shop", "O", "Retail", "Maun", "x", email="cardshop@example.com", password="correct-horse-battery")
    oid = opportunity_service.create_opportunity(bid, "Survey shops", "d", None, 0)
    agent_service.person_apply(AGENT, "Mpho", pid, oid)
    aid = agent_service.person_work(AGENT, pid)[0]["assignment_id"]
    with pytest.raises(ValueError):                       # not accepted yet
        agent_service.person_start_work(AGENT, "Mpho", pid, aid)
    assignment_service.accept_assignment(aid)
    with pytest.raises(ValueError):                       # another agent's person
        agent_service.person_start_work("agent-key-3", "Kabo", pid, aid)
    agent_service.person_start_work(AGENT, "Mpho", pid, aid)
    trial = agent_service.person_work(AGENT, pid)[0]["trial_id"]
    agent_service.person_submit_trial(AGENT, "Mpho", pid, trial, dict(GOOD))
    sub = agent_service.person_trials(AGENT, pid)[0]
    assert sub["status"] == "Submitted" and sub["submission"]["type"] == "field_card" and sub["submission"]["summary"] == "Bookings are on paper"
    assert agent_service.person_trials(None, other) == []
