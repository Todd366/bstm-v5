"""No database needed: validators, hashing, scoring."""

import pytest

from app.core.validation import clean_email, clean_text, clean_url, require_uuid
from app.services.auth_service import (
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from app.services.matching_service import calculate_match_score


def test_clean_text_rules():
    assert clean_text("  hi  ", "X", 10) == "hi"
    assert clean_text("", "X", 10, required=False) is None
    with pytest.raises(ValueError, match="required"):
        clean_text("  ", "X", 10)
    with pytest.raises(ValueError, match="at most"):
        clean_text("x" * 11, "X", 10)


def test_email_validation():
    assert clean_email(" a@b.co ") == "a@b.co"
    for bad in ("nope", "a@b", "a b@c.com", ""):
        with pytest.raises(ValueError):
            clean_email(bad)


def test_uuid_validation_reports_not_found():
    assert require_uuid("123e4567-e89b-12d3-a456-426614174000", "X")
    with pytest.raises(ValueError, match="not found"):
        require_uuid("abc", "X")


def test_url_must_be_http():
    assert clean_url("https://example.com/a") == "https://example.com/a"
    assert clean_url("", required=False) is None if False else True
    for bad in ("javascript:alert(1)", "data:text/html,x", "ftp://x.com", "example.com"):
        with pytest.raises(ValueError):
            clean_url(bad)


def test_password_rules_and_hash_roundtrip():
    validate_password("long-enough")
    with pytest.raises(ValueError):
        validate_password("short")
    with pytest.raises(ValueError):
        validate_password("x" * 129)

    stored = hash_password("secret-pass", iterations=1000)
    assert verify_password("secret-pass", stored)
    assert not verify_password("other-pass", stored)
    assert needs_rehash(stored)
    assert not needs_rehash(hash_password("secret-pass"))
    assert not verify_password("x", "garbage")


def test_score_needs_a_real_text_match():
    # level / verification never create a match on their own
    assert calculate_match_score("Plumbing", "Trades", "Expert", True, "Web design", "A website") == 0
    # a category word only in the description is too weak
    assert calculate_match_score("Plumbing", "Business", "Expert", True, "Fix taps", "for a business") == 0
    assert calculate_match_score("Plumbing", "Trades", "Beginner", False, "Plumbing job", "") == 50


def test_score_uses_whole_words():
    assert calculate_match_score("AI", "Technology", "Beginner", False, "Retail email", "") == 0
    assert calculate_match_score("AI", "Technology", "Beginner", False, "AI chatbot", "") == 50
