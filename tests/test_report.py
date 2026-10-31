"""Monthly report reads live rows and respects the month."""
import pytest
from app.core.permissions import is_allowed
from app.services import report_service
from tests.helpers import create_youth


def test_counts_new_people_this_month_only(test_database):
    before = report_service.monthly_report()
    create_youth(name="Report Person")
    after = report_service.monthly_report()
    assert after["people_joined"] == before["people_joined"] + 1
    assert after["total"]["people"] == before["total"]["people"] + 1
    assert report_service.monthly_report("2001-01")["people_joined"] == 0
    assert "BSTM Activation" in report_service.report_text(after)


def test_bad_month_is_refused_and_roles_limited(test_database):
    for bad in ("2026-13", "last month", "2026-1"):
        with pytest.raises(ValueError):
            report_service.monthly_report(bad)
    assert is_allowed("finance", "GET", "/admin/report")
    assert not is_allowed("support", "GET", "/admin/report")


def test_csv_and_agent_rows_and_payload_budget(test_database):
    from app.services import agent_service
    agent_service.register_person("agent-x", "Mpho", "Csv Person", "76123456", "Maun", None, True)
    r = report_service.monthly_report()
    assert r["agents"] and r["agents"][0]["registered"] >= 1
    csv = report_service.report_csv(r)
    assert csv.startswith("metric,value\n") and '"people_joined"' in csv


def test_first_load_stays_small():
    """Budget for slow 2G: app shell under 150 KB gzipped (roadmap Phase 2)."""
    import gzip, pathlib
    total = sum(len(gzip.compress(p.read_bytes())) for p in pathlib.Path("public").iterdir() if p.suffix in (".js", ".css", ".html", ".svg", ".webmanifest"))
    assert total < 150 * 1024, total


def test_report_by_town_and_staff_job_list_shows_skills(test_database):
    from app.services import business_service, capability_service, opportunity_service
    web = capability_service.create_capability("Web Design", "Technology")
    bid = business_service.create_business("Town Shop", "O", "Retail", "Kasane", "x", email="town@example.com", password="correct-horse-battery")
    oid = opportunity_service.create_opportunity(bid, "Site", "d", None, 100, skills=[web])
    towns = {t["town"]: t for t in report_service.monthly_report()["towns"]}
    assert towns["Kasane"]["jobs"] == 1
    listed = [o for o in opportunity_service.list_opportunities() if o["id"] == oid][0]
    assert listed["required_skills"] == ["Web Design"]
    assert "town: Kasane jobs" in report_service.report_csv(report_service.monthly_report())
