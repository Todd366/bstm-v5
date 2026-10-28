"""Department recommendation + first-steps brief for a youth, computed
from the questionnaire answers stored in youth.intake."""

from app.core.department_catalog import CATALOG
from app.core.validation import require_uuid
from app.db.database import transaction

TAG_MAP = {
    "Technology": "technology", "Business": "business", "Creative": "creative",
    "Agriculture": "agriculture", "Trades": "trades", "Finance": "finance",
    "Research": "research", "Community": "community",
}
# Department categories that have no skills of the same name borrow from these
# (ported from the old v3 skill-gap tables, now driven by the live skill catalogue).
SKILL_CATEGORIES = {"Operations": ["Business", "Finance", "Trades"]}
RANK = {"low": 0, "medium": 1, "high": 2}

MISSION = {
    "Technology": "Build and ship a working {entry} for a real BSTM-connected business.",
    "Creative": "Produce a first body of {entry} for an active BSTM client or trial business.",
    "Operations": "Take ownership of one real operational task in {name}: {entry}.",
    "Research": "Contribute field evidence to {name} through {entry}.",
    "Agriculture": "Run a small, documented pilot in {entry}.",
}


def _as_list(value):
    return [str(v) for v in value] if isinstance(value, list) else []


def score_departments(intake):
    intake = intake or {}
    tags = {TAG_MAP[i] for i in _as_list(intake.get("interests")) if i in TAG_MAP}
    n = len(_as_list(intake.get("resources")))
    level = "high" if n >= 4 else "medium" if n >= 2 else "low"
    full_time = intake.get("availability") == "Full-time"

    ranked = []
    for dept in CATALOG:
        score = 34 * len(tags.intersection(dept["tags"]))
        score += 20 if RANK[dept["resource"]] <= RANK[level] else -15
        if full_time:
            score += 8
        ranked.append(dict(dept, score=max(0, min(100, score))))

    ranked.sort(key=lambda d: (-d["score"], d["name"]))
    return ranked


def build_brief(intake):
    intake = intake or {}
    ranked = score_departments(intake)
    primary = ranked[0]
    challenges = _as_list(intake.get("challenges"))

    return {
        "primary": primary,
        "alternatives": ranked[1:4],
        "mission": MISSION.get(primary["category"], MISSION["Operations"]).format(
            entry=primary["entry"].lower(), name=primary["name"]
        ),
        "priorities": [
            "Complete your first BSTM trial in " + primary["name"],
            "Add proof of your work: every trial builds your profile",
            "Get introduced to one other builder in this department"
            if "No network" in challenges
            else "Ask for a second opportunity once the first is reviewed",
        ],
        "learning_path": [
            "Orientation: how " + primary["name"] + " works inside BSTM",
            "Study one completed example",
            "Attempt your first guided trial",
            "Submit for review and receive feedback",
        ],
    }


def skills_to_learn(db, youth_id, primary_category, limit=5):
    """Catalogue skills in the youth's best-fit area that they have not claimed yet."""

    categories = SKILL_CATEGORIES.get(primary_category, [primary_category])
    marks = ",".join("?" * len(categories))
    rows = db.execute(
        "SELECT c.name, c.category, c.description FROM capabilities c "
        "WHERE c.category IN (" + marks + ") "
        "AND NOT EXISTS (SELECT 1 FROM youth_capabilities yc WHERE yc.youth_id = ? AND yc.capability_id = c.id) "
        "ORDER BY c.category, c.name LIMIT ?",
        tuple(categories) + (youth_id, limit),
    ).fetchall()

    return [dict(r) for r in rows]


def get_brief(youth_id):
    youth_id = require_uuid(youth_id, "Youth")

    with transaction() as db:
        row = db.execute("SELECT intake FROM youth WHERE id = ?", (youth_id,)).fetchone()

        if not row:
            raise ValueError("Youth not found")

        brief = build_brief(row["intake"])
        brief["skills_to_learn"] = skills_to_learn(db, youth_id, brief["primary"]["category"])

    return brief
