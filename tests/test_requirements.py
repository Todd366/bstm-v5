"""Structured job requirements drive matching exactly."""

import pytest

from app.services import business_service, capability_service, matching_service, opportunity_service
from app.services.matching_service import requirement_score
from tests.helpers import create_youth

PW = "correct-horse-battery"


def test_requirement_score_rules():
    owned = {"a": ("Advanced", True), "b": ("Beginner", False)}
    assert requirement_score({"x"}, owned) == (0, [])
    full, covered = requirement_score({"a", "b"}, owned)
    half, _ = requirement_score({"a", "x"}, owned)
    assert full > half > 0 and len(covered) == 2 and full <= 100
    assert requirement_score({"b"}, owned)[0] < requirement_score({"a"}, owned)[0]


def _job(skills, title="Fix my shop thing"):
    bid = business_service.create_business("Req Shop", "Owner", "Retail", "Maun", "x", email="req@example.com", password=PW)
    return opportunity_service.create_opportunity(bid, title, "Needs hands", None, 100, skills=skills)


def test_job_matches_by_named_skills_not_by_wording(test_database):
    web = capability_service.create_capability("Web Development", "Technology")
    poster = capability_service.create_capability("Graphic Design", "Creative")
    oid = _job([web], title="Help with my shop")        # title says nothing about the skill

    coder = create_youth(name="Coder", location="Maun")
    artist = create_youth(name="Artist", location="Maun")
    capability_service.assign_capability_to_youth(coder, web, "Advanced")
    capability_service.assign_capability_to_youth(artist, poster, "Advanced")

    mine = matching_service.match_youth_to_opportunities(coder)
    assert [m["opportunity_id"] for m in mine] == [oid] and mine[0]["required_skills"] == ["Web Development"]
    assert matching_service.match_youth_to_opportunities(artist) == []

    cands = matching_service.candidates_for_opportunity(oid)
    assert [c["name"] for c in cands] == ["Coder"]


def test_partial_coverage_is_scored_lower_and_explained(test_database):
    a = capability_service.create_capability("Sales", "Business")
    b = capability_service.create_capability("Bookkeeping", "Finance")
    oid = _job([a, b])
    both = create_youth(name="Both")
    one = create_youth(name="One")
    for cap in (a, b):
        capability_service.assign_capability_to_youth(both, cap, "Intermediate")
    capability_service.assign_capability_to_youth(one, a, "Intermediate")

    s_both = matching_service.match_youth_to_opportunities(both)[0]
    s_one = matching_service.match_youth_to_opportunities(one)[0]
    assert s_both["match_score"] > s_one["match_score"]
    assert any("Still to add" in r for r in s_one["reasons"])


def test_skill_limits_and_validation(test_database):
    caps = [capability_service.create_capability("Skill %d" % i, "Business") for i in range(6)]
    with pytest.raises(ValueError):
        _job(caps)
    with pytest.raises(ValueError):
        _job(["00000000-0000-4000-8000-0000000000aa"])
    with pytest.raises(ValueError):
        _job(["not-a-uuid"])


def test_browse_shows_required_skills(test_database):
    s = capability_service.create_capability("Painting", "Trades")
    _job([s])
    rows = opportunity_service.browse_open_opportunities(create_youth(name="Browser"))
    assert rows[0]["required_skills"] == ["Painting"]
