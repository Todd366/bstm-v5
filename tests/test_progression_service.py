"""
Pure-logic tests for the progression engine. Deliberately no database
dependency — compute_level() and capability_gain_for_review() are pure
functions, so these tests run anywhere, including CI, with no fixture
and no BSTM_DATABASE_URL needed.
"""

from app.services.progression_service import (
    capability_gain_for_review,
    compute_level,
)


def test_zero_everything_is_explorer():
    assert compute_level(0, 0, 0, 0) == "Explorer"


def test_meets_learner_threshold():
    assert compute_level(1, 0, 5, 40) == "Learner"


def test_meets_trial_builder_threshold():
    assert compute_level(3, 0, 15, 50) == "Trial Builder"


def test_meets_contributor_threshold():
    assert compute_level(5, 1, 30, 55) == "Contributor"


def test_meets_specialist_threshold():
    assert compute_level(12, 6, 75, 70) == "Specialist"


def test_quality_gate_blocks_advancement_despite_high_counts():
    """Counts alone qualify for Specialist, but reliability (45) only
    clears Learner's floor (40), not Trial Builder's (50) — advancement
    must be capped at Learner, not driven by counts alone."""

    assert compute_level(12, 6, 75, 45) == "Learner"


def test_count_gate_blocks_advancement_despite_high_quality():
    """Quality is maxed out, but zero completed work — must stay at
    Explorer regardless of how high the scores are."""

    assert compute_level(0, 0, 100, 100) == "Explorer"


def test_capability_gain_defaults_when_no_review_given():
    assert capability_gain_for_review(None) == 4
    assert capability_gain_for_review({}) == 4


def test_capability_gain_scales_with_review_score():
    assert capability_gain_for_review({"score": 100}) == 8.0
    assert capability_gain_for_review({"score": 50}) == 4.0


def test_capability_gain_handles_malformed_score():
    assert capability_gain_for_review({"score": "not a number"}) == 4


def test_capability_gain_clamps_out_of_range_score():
    assert capability_gain_for_review({"score": 150}) == 8.0
    assert capability_gain_for_review({"score": -50}) == 0.0
