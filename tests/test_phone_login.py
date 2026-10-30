"""Young people can sign up, log in and reset with a phone number."""
import pytest
from app.core.validation import clean_phone, split_login_id
from app.services import reset_service, youth_service
from app.services.youth_service import authenticate_youth

PW = "correct-horse-battery"


def test_phone_formats_normalise_and_bad_ones_fail():
    for raw in ("71234567", "071234567", "+267 71 234 567", "26771234567", "71-234-567"):
        assert clean_phone(raw) == "+26771234567"
    for bad in ("1234", "81234567", "abc", "", "+27 71 234 5678"):
        with pytest.raises(ValueError):
            clean_phone(bad)
    assert split_login_id("A@b.co")[0] == "email" and split_login_id("71234567")[0] == "phone"


def test_signup_login_duplicate_and_reset_by_phone(test_database):
    yid = youth_service.create_youth("Kago Phone", "Maun", "Work", None, PW, phone="071 234 567")
    assert authenticate_youth("71234567", PW) == yid
    assert authenticate_youth("+267 71234567", PW) == yid
    with pytest.raises(ValueError):
        authenticate_youth("71234567", "wrong-password-here")
    with pytest.raises(Exception):
        youth_service.create_youth("Copy", "Maun", "Work", None, PW, phone="71234567")
    with pytest.raises(ValueError):
        youth_service.create_youth("Nobody", "Maun", "Work", None, PW)
    code = reset_service.create_reset_code("youth", "71234567")["code"]
    reset_service.redeem_reset_code("youth", "+26771234567", code, "brand-new-password-1")
    assert authenticate_youth("71234567", "brand-new-password-1") == yid
    assert youth_service.get_youth(yid)["phone"] == "+26771234567"
