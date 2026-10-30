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
