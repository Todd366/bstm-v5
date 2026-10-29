"""The 100 Trials field card is validated on the server."""
import pytest
from app.services.field_card import normalise_field_card

GOOD = {"type": "field_card", "trial_no": 3, "date": "2026-10-29", "business": "Thabo's Salon", "btype": "salon", "size": "S", "location": "Maun",
        "entry_type": "walk-in", "reaction": "friendly", "asked": [True, False], "quotes": ["We lose customers on Fridays", ""],
        "core_problem": "Bookings are on paper", "insight": "Double bookings", "interest": "yes", "return": "no", "scores": {"a": "7", "t": 5}}


def test_good_card_is_cleaned_and_keeps_summary():
    c = normalise_field_card(dict(GOOD))
    assert c["summary"] == "Bookings are on paper" and c["quotes"] == ["We lose customers on Fridays"]
    assert c["asked"] == [True, False, False, False] and c["scores"] == {"a": 7, "t": 5}


def test_bad_cards_are_refused():
    for change in [{"core_problem": ""}, {"btype": "mine"}, {"quotes": []}, {"date": "tomorrow"}, {"scores": {"a": 11}}, {"link": "ftp://x"}]:
        with pytest.raises(ValueError):
            normalise_field_card({**GOOD, **change})
