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
