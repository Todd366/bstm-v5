"""
Progression engine.

Turns youth.level / capability_score / reliability_score from inert
defaults into fields that move based on real completed work.

DESIGN DECISION: level advancement requires BOTH a minimum amount of
completed work (trials + opportunities) AND a minimum quality bar
(capability_score, reliability_score) — a pure count gate can be gamed
by grinding low-effort trials; a pure score gate has no natural floor
tied to actual output. This mirrors the product's own stated principle
of claimed vs. demonstrated vs. verified capability.

Level is always recomputed live from current scores/counts rather than
only ratcheting upward — a youth whose reliability drops (e.g. from
cancelled trials) after advancing can genuinely drop a level. This is a
deliberate choice: level reflects current standing, not a permanent
badge once earned.

SCOPE: only levels reachable with the current data model are
implemented (Explorer through Specialist). Department Member / Team
Leader / Project Builder / Ecosystem Builder require department and
leadership features that don't exist in the schema yet — adding gates
for them now would be guessing at requirements, not architecture.
learning_score is intentionally not gated on yet either: it needs a
longer history of score-over-time to mean anything, and there isn't
enough real usage data yet to design that honestly.
"""

import json


LEVELS = [
    {
        "name": "Explorer",
        "min_completed_trials": 0,
        "min_completed_opportunities": 0,
        "min_capability_score": 0,
        "min_reliability_score": 0,
    },
    {
        "name": "Learner",
        "min_completed_trials": 1,
        "min_completed_opportunities": 0,
        "min_capability_score": 5,
        "min_reliability_score": 40,
    },
    {
        "name": "Trial Builder",
        "min_completed_trials": 3,
        "min_completed_opportunities": 0,
        "min_capability_score": 15,
        "min_reliability_score": 50,
    },
    {
        "name": "Contributor",
        "min_completed_trials": 5,
        "min_completed_opportunities": 1,
        "min_capability_score": 30,
        "min_reliability_score": 55,
    },
    {
        "name": "Service Provider",
        "min_completed_trials": 8,
        "min_completed_opportunities": 3,
        "min_capability_score": 50,
        "min_reliability_score": 60,
    },
    {
        "name": "Specialist",
        "min_completed_trials": 12,
        "min_completed_opportunities": 6,
        "min_capability_score": 75,
        "min_reliability_score": 70,
    },
]

LEVEL_NAMES = [level["name"] for level in LEVELS]

CAPABILITY_SCORE_CAP = 100
RELIABILITY_SCORE_CAP = 100
RELIABILITY_SCORE_FLOOR = 0

# How much a completed trial moves capability_score, scaled by the
# review's 0-100 `score` field if reviewers provided one.
CAPABILITY_GAIN_PER_TRIAL_MAX = 8
CAPABILITY_GAIN_PER_TRIAL_DEFAULT = 4

RELIABILITY_GAIN_ON_COMPLETE = 3
RELIABILITY_LOSS_ON_CANCEL = 8


def compute_level(completed_trials, completed_opportunities, capability_score, reliability_score):
    """Returns the highest level whose requirements are all currently met."""

    earned = LEVELS[0]["name"]

    for level in LEVELS:
        if (
            completed_trials >= level["min_completed_trials"]
            and completed_opportunities >= level["min_completed_opportunities"]
            and capability_score >= level["min_capability_score"]
            and reliability_score >= level["min_reliability_score"]
        ):
            earned = level["name"]

    return earned


def capability_gain_for_review(review):
    """Extracts a 0-100 `score` from a trial's review payload, if
    present, and scales it into a capability_score gain. Falls back to
    a modest fixed gain when no score was supplied, so completing a
    trial still counts for something even without a formal review."""

    if not review or "score" not in review:
        return CAPABILITY_GAIN_PER_TRIAL_DEFAULT

    try:
        score = float(review["score"])
    except (TypeError, ValueError):
        return CAPABILITY_GAIN_PER_TRIAL_DEFAULT

    score = max(0, min(100, score))
    return round((score / 100) * CAPABILITY_GAIN_PER_TRIAL_MAX, 2)


def apply_progression(db, youth_id, capability_delta=0, reliability_delta=0):
    """Applies score deltas to a youth (clamped to valid ranges), then
    recomputes and persists their level. Call this from inside an
    existing `transaction()` block — it does not open its own, so the
    score/level update is part of the same commit as whatever action
    (trial completion, cancellation, etc.) triggered it."""

    youth = db.execute(
        """
        SELECT completed_trials, completed_opportunities,
               capability_score, reliability_score, level
        FROM youth
        WHERE id = ?
        """,
        (youth_id,),
    ).fetchone()

    if not youth:
        raise ValueError("Youth not found")

    new_capability = max(
        0,
        min(CAPABILITY_SCORE_CAP, float(youth["capability_score"]) + capability_delta),
    )
    new_reliability = max(
        RELIABILITY_SCORE_FLOOR,
        min(RELIABILITY_SCORE_CAP, float(youth["reliability_score"]) + reliability_delta),
    )

    new_level = compute_level(
        youth["completed_trials"],
        youth["completed_opportunities"],
        new_capability,
        new_reliability,
    )

    db.execute(
        """
        UPDATE youth
        SET capability_score = ?, reliability_score = ?, level = ?, updated_at = now()
        WHERE id = ?
        """,
        (new_capability, new_reliability, new_level, youth_id),
    )

    old_level = youth["level"]

    if new_level != old_level:

        old_index = LEVEL_NAMES.index(old_level) if old_level in LEVEL_NAMES else -1
        new_index = LEVEL_NAMES.index(new_level)

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "level_advanced" if new_index > old_index else "level_dropped",
                youth_id,
                youth_id,
                json.dumps(
                    {
                        "youth_id": str(youth_id),
                        "old_level": old_level,
                        "new_level": new_level,
                        "capability_score": new_capability,
                        "reliability_score": new_reliability,
                    }
                ),
            ),
        )

    return {
        "level": new_level,
        "capability_score": new_capability,
        "reliability_score": new_reliability,
    }
