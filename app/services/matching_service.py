import json
import re

import psycopg2.extras

from app.core.validation import require_uuid
from app.db.database import transaction


LEVEL_WEIGHTS = {
    "Beginner": 0,
    "Developing": 5,
    "Intermediate": 10,
    "Advanced": 15,
    "Expert": 20,
}

LOCATION_BONUS = 10
MAX_CANDIDATES = 300

_word_cache = {}


def _contains_term(text, term):
    """Whole-word / whole-phrase match, so a capability called "AI" does
    not match "retail" or "email"."""

    if not term or not text:
        return False

    pattern = _word_cache.get(term)

    if pattern is None:
        pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)")
        _word_cache[term] = pattern

    return bool(pattern.search(text))


def calculate_match_score(
    capability_name,
    capability_category,
    level,
    verified,
    opportunity_title,
    opportunity_description,
):
    """0-100 fit between one claimed capability and one opportunity.
    Returns 0 when the opportunity's text mentions neither the
    capability nor its category (level and verification only ever
    strengthen a real text match, they never create one)."""

    title = (opportunity_title or "").lower()
    description = (opportunity_description or "").lower()
    name = (capability_name or "").lower().strip()
    category = (capability_category or "").lower().strip()

    score = 0
    name_hit = False
    strong_category_hit = False

    if _contains_term(title, name):
        score += 50
        name_hit = True
    elif _contains_term(description, name):
        score += 30
        name_hit = True

    if _contains_term(title, category):
        score += 20
        strong_category_hit = True
    elif _contains_term(description, category):
        score += 10

    # A category word alone in the description ("business", "community")
    # is too common to mean anything: require the capability's own name,
    # or its category in the title.
    if not (name_hit or strong_category_hit):
        return 0

    if score == 0:
        return 0

    score += LEVEL_WEIGHTS.get(level, 0)

    if verified:
        score += 10

    return min(score, 100)


def requirement_score(required_ids, owned):
    """Fit between the skills a job asks for and what a youth has.

    required_ids: set of capability ids the job names.
    owned: {capability_id: (level, verified)} for the youth.
    Returns (score 0-100, covered ids). 0 when none of the skills are held:
    60 points for coverage, up to 20 for the best level, 10 if any is verified
    by BSTM, 10 if every required skill is held."""

    covered = [c for c in required_ids if c in owned]

    if not covered:
        return 0, []

    score = round(60 * len(covered) / len(required_ids))
    score += max(LEVEL_WEIGHTS.get(owned[c][0], 0) for c in covered)

    if any(owned[c][1] for c in covered):
        score += 10

    if len(covered) == len(required_ids):
        score += 10

    return min(score, 100), covered


def _requirements(db, opportunity_ids):
    """{opportunity_id: {capability_id: name}} for the given jobs."""

    if not opportunity_ids:
        return {}

    marks = ",".join("?" * len(opportunity_ids))
    rows = db.execute(
        "SELECT r.opportunity_id, r.capability_id, c.name FROM opportunity_requirements r "
        "JOIN capabilities c ON c.id = r.capability_id WHERE r.opportunity_id IN (" + marks + ")",
        tuple(opportunity_ids),
    ).fetchall()

    out = {}
    for r in rows:
        out.setdefault(str(r["opportunity_id"]), {})[str(r["capability_id"])] = r["name"]
    return out


def _same_place(a, b):
    """Loose place match: 'Mochudi' vs 'mochudi, kgatleng' → True."""

    a = (a or "").lower().strip()
    b = (b or "").lower().strip()

    if not a or not b:
        return False

    return a in b or b in a


def match_youth_to_opportunities(youth_id, limit=50):
    """Open opportunities that fit this youth's claimed capabilities,
    best first — one row per opportunity, with the capability that
    matched best. Opportunities the youth already applied to are left
    out. Opportunities in the youth's own town/village get a bonus.
    Includes department-sourced opportunities (no business)."""

    youth_id = require_uuid(youth_id, "Youth")
    limit = max(1, min(int(limit), 100))

    with transaction() as db:

        youth = db.execute(
            "SELECT id, name, location FROM youth WHERE id = ?",
            (youth_id,),
        ).fetchone()

        if not youth:
            raise ValueError("Youth not found")

        capabilities = db.execute(
            """
            SELECT yc.capability_id, c.name AS capability_name,
                   c.category AS capability_category, yc.level, yc.verified
            FROM youth_capabilities yc
            JOIN capabilities c ON c.id = yc.capability_id
            WHERE yc.youth_id = ?
            """,
            (youth_id,),
        ).fetchall()

        if not capabilities:
            return []

        opportunities = db.execute(
            """
            SELECT o.id AS opportunity_id, o.business_id,
                   b.name AS business_name, b.location AS business_location,
                   o.title, o.description, o.department, o.budget,
                   o.status, o.created_at
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE o.status = 'Open' AND o.approval_status = 'Approved'
              AND NOT EXISTS (
                  SELECT 1 FROM opportunity_assignments oa
                  WHERE oa.opportunity_id = o.id AND oa.youth_id = ?
              )
            ORDER BY o.created_at DESC
            LIMIT ?
            """,
            (youth_id, MAX_CANDIDATES),
        ).fetchall()

        reqs = _requirements(db, [o["opportunity_id"] for o in opportunities])

    results = []
    owned = {str(c["capability_id"]): (c["level"], c["verified"]) for c in capabilities}

    for opp in opportunities:

        required = reqs.get(str(opp["opportunity_id"]))

        if required:
            score, covered = requirement_score(set(required), owned)

            if score <= 0:
                continue

            cap = next(c for c in capabilities if str(c["capability_id"]) in covered)
            names = [required[c] for c in covered]
            reasons = ["Has the skills this job asks for: " + ", ".join(names)]

            if len(covered) < len(required):
                missing = [n for c, n in required.items() if c not in covered]
                reasons.append("Still to add: " + ", ".join(missing))

            if _same_place(youth["location"], opp["business_location"]):
                score = min(100, score + LOCATION_BONUS)
                reasons.append("In your area")

            result = dict(opp)
            result.update({
                "match_score": score, "capability_id": cap["capability_id"], "capability_name": cap["capability_name"],
                "capability_category": cap["capability_category"], "level": cap["level"], "verified": cap["verified"],
                "matched_capabilities": names, "reasons": reasons, "required_skills": sorted(required.values()),
            })
            results.append(result)
            continue

        searchable_description = " ".join(
            part for part in (opp["description"], opp["department"]) if part
        )

        best = None
        matched_names = []

        for cap in capabilities:

            score = calculate_match_score(
                capability_name=cap["capability_name"],
                capability_category=cap["capability_category"],
                level=cap["level"],
                verified=cap["verified"],
                opportunity_title=opp["title"],
                opportunity_description=searchable_description,
            )

            if score <= 0:
                continue

            matched_names.append(cap["capability_name"])

            if best is None or score > best[0]:
                best = (score, cap)

        if best is None:
            continue

        score, cap = best
        reasons = ["Matches your skill: " + cap["capability_name"]]

        if _same_place(youth["location"], opp["business_location"]):
            score = min(100, score + LOCATION_BONUS)
            reasons.append("In your area")

        result = dict(opp)
        result.update(
            {
                "match_score": score,
                "capability_id": cap["capability_id"],
                "capability_name": cap["capability_name"],
                "capability_category": cap["capability_category"],
                "level": cap["level"],
                "verified": cap["verified"],
                "matched_capabilities": matched_names,
                "reasons": reasons,
            }
        )
        results.append(result)

    results.sort(key=lambda r: (r["match_score"], r["created_at"]), reverse=True)

    return results[:limit]


def create_opportunity_match(youth_id, opportunity_id, match_score=0, reason=None):

    youth_id = require_uuid(youth_id, "Youth")
    opportunity_id = require_uuid(opportunity_id, "Opportunity")

    with transaction() as db:

        youth = db.execute(
            "SELECT id, name FROM youth WHERE id = ?",
            (youth_id,),
        ).fetchone()

        if not youth:
            raise ValueError("Youth not found")

        opportunity = db.execute(
            "SELECT id, business_id, title, status FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()

        if not opportunity:
            raise ValueError("Opportunity not found")

        existing = db.execute(
            "SELECT id FROM opportunity_matches WHERE youth_id = ? AND opportunity_id = ?",
            (youth_id, opportunity_id),
        ).fetchone()

        if existing:
            return str(existing["id"])

        reason_param = psycopg2.extras.Json(reason) if reason is not None else None

        row = db.execute(
            """
            INSERT INTO opportunity_matches (
                youth_id, opportunity_id, match_score, reason, status
            )
            VALUES (?, ?, ?, ?, 'Suggested')
            ON CONFLICT (youth_id, opportunity_id) DO NOTHING
            RETURNING id
            """,
            (youth_id, opportunity_id, match_score, reason_param),
        ).fetchone()

        if row is None:
            # Lost a race with a concurrent identical request.
            row = db.execute(
                "SELECT id FROM opportunity_matches WHERE youth_id = ? AND opportunity_id = ?",
                (youth_id, opportunity_id),
            ).fetchone()
            return str(row["id"])

        match_id = row["id"]

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "opportunity_matched",
                youth_id,
                opportunity_id,
                json.dumps(
                    {
                        "match_id": str(match_id),
                        "match_score": float(match_score),
                    }
                ),
            ),
        )

    return str(match_id)


def list_youth_matches(youth_id):

    youth_id = require_uuid(youth_id, "Youth")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                om.id AS match_id,
                om.youth_id,
                om.opportunity_id,
                om.match_score,
                om.reason,
                om.status,
                om.created_at,
                o.title,
                o.description,
                o.status AS opportunity_status,
                b.name AS business_name
            FROM opportunity_matches om
            JOIN opportunities o
                ON o.id = om.opportunity_id
            LEFT JOIN businesses b
                ON b.id = o.business_id
            WHERE om.youth_id = ?
            ORDER BY om.match_score DESC, om.created_at DESC
            """,
            (youth_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def candidates_for_opportunity(opportunity_id, limit=20):
    """Youth whose claimed skills fit this opportunity, best first.
    Excludes youth who already applied or were offered it."""

    opportunity_id = require_uuid(opportunity_id, "Opportunity")
    limit = max(1, min(int(limit), 50))

    with transaction() as db:

        opp = db.execute(
            """
            SELECT o.id, o.title, o.description, o.department, b.location
            FROM opportunities o LEFT JOIN businesses b ON b.id = o.business_id
            WHERE o.id = ?
            """,
            (opportunity_id,),
        ).fetchone()

        if not opp:
            raise ValueError("Opportunity not found")

        rows = db.execute(
            """
            SELECT y.id AS youth_id, y.name, y.location, y.level,
                   c.name AS capability_name, c.category AS capability_category,
                   yc.level AS cap_level, yc.verified, yc.capability_id
            FROM youth y
            JOIN youth_capabilities yc ON yc.youth_id = y.id
            JOIN capabilities c ON c.id = yc.capability_id
            WHERE y.deleted_at IS NULL AND NOT EXISTS (
                SELECT 1 FROM opportunity_assignments oa
                WHERE oa.opportunity_id = ? AND oa.youth_id = y.id
            )
            """,
            (opportunity_id,),
        ).fetchall()

        required = _requirements(db, [opportunity_id]).get(opportunity_id, {})

    text = " ".join(p for p in (opp["description"], opp["department"]) if p)
    best = {}

    if required:
        people = {}
        for r in rows:
            person = people.setdefault(r["youth_id"], {"row": r, "owned": {}})
            person["owned"][str(r["capability_id"])] = (r["cap_level"], r["verified"])

        for yid, person in people.items():
            score, covered = requirement_score(set(required), person["owned"])
            if score <= 0:
                continue
            r = person["row"]
            if _same_place(r["location"], opp["location"]):
                score = min(100, score + LOCATION_BONUS)
            best[yid] = {
                "youth_id": yid, "name": r["name"], "location": r["location"], "level": r["level"],
                "capability_name": ", ".join(required[c] for c in covered),
                "verified": any(person["owned"][c][1] for c in covered), "match_score": score,
                "covers": "%d of %d required skills" % (len(covered), len(required)),
            }

        return sorted(best.values(), key=lambda c: -c["match_score"])[:limit]

    for r in rows:
        score = calculate_match_score(
            r["capability_name"], r["capability_category"], r["cap_level"],
            r["verified"], opp["title"], text,
        )
        if score <= 0:
            continue
        if _same_place(r["location"], opp["location"]):
            score = min(100, score + LOCATION_BONUS)
        cur = best.get(r["youth_id"])
        if cur is None or score > cur["match_score"]:
            best[r["youth_id"]] = {
                "youth_id": r["youth_id"], "name": r["name"], "location": r["location"],
                "level": r["level"], "capability_name": r["capability_name"],
                "verified": r["verified"], "match_score": score,
            }

    return sorted(best.values(), key=lambda c: -c["match_score"])[:limit]
