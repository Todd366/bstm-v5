#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/bstm-activation/bstm_v5

echo "Backing up..."
cp bstm.db "bstm_pre_patch1_$(date +%Y%m%d_%H%M%S).db" 2>/dev/null || true

echo "Fixing ID generation (8-char -> full uuid4, removes collision risk)..."
cat << 'PYEOF' > app/core/ids.py
import uuid


def generate_id(
    prefix
):

    return (
        f"{prefix}-"
        f"{uuid.uuid4().hex}"
    )
PYEOF

echo "Replacing fake LIKE-matching with a real weighted scoring engine..."
cat << 'PYEOF' > app/services/matching_service.py
import json

from app.core.ids import generate_id
from app.core.time import utc_now
from app.db.database import transaction


LEVEL_WEIGHTS = {
    "Beginner": 0,
    "Developing": 5,
    "Intermediate": 10,
    "Advanced": 15,
    "Expert": 20
}


def calculate_match_score(
    capability_name,
    capability_category,
    level,
    verified,
    opportunity_title,
    opportunity_description
):

    score = 0

    title = (opportunity_title or "").lower()
    description = (opportunity_description or "").lower()
    name = (capability_name or "").lower()
    category = (capability_category or "").lower()

    if name and name in title:
        score += 50
    elif name and name in description:
        score += 30

    if category and category in title:
        score += 20
    elif category and category in description:
        score += 10

    score += LEVEL_WEIGHTS.get(level, 0)

    if verified:
        score += 10

    return min(score, 100)


def match_youth_to_opportunities(
    youth_id
):

    if not youth_id:
        raise ValueError(
            "Youth ID is required"
        )

    with transaction() as db:

        youth = db.execute(
            """
            SELECT
                id,
                name
            FROM youth
            WHERE id = ?
            """,
            (
                youth_id,
            )
        ).fetchone()

        if not youth:

            raise ValueError(
                "Youth not found"
            )

        rows = db.execute(
            """
            SELECT DISTINCT
                o.id AS opportunity_id,
                o.business_id,
                b.name AS business_name,
                o.title,
                o.description,
                o.status,
                yc.capability_id,
                c.name AS capability_name,
                c.category AS capability_category,
                yc.level,
                yc.verified
            FROM opportunities o
            JOIN businesses b
                ON b.id = o.business_id
            JOIN youth_capabilities yc
                ON yc.youth_id = ?
            JOIN capabilities c
                ON c.id = yc.capability_id
            WHERE o.status = 'Open'
            AND (
                LOWER(o.title) LIKE '%' || LOWER(c.name) || '%'
                OR LOWER(COALESCE(o.description, '')) LIKE '%' || LOWER(c.name) || '%'
                OR LOWER(o.title) LIKE '%' || LOWER(c.category) || '%'
                OR LOWER(COALESCE(o.description, '')) LIKE '%' || LOWER(c.category) || '%'
            )
            """,
            (
                youth_id,
            )
        ).fetchall()

    results = [dict(row) for row in rows]

    for result in results:
        result["match_score"] = calculate_match_score(
            capability_name=result["capability_name"],
            capability_category=result["capability_category"],
            level=result["level"],
            verified=result["verified"],
            opportunity_title=result["title"],
            opportunity_description=result["description"]
        )

    results.sort(key=lambda r: r["match_score"], reverse=True)

    return results


def create_opportunity_match(
    youth_id,
    opportunity_id,
    match_score=0,
    reason=None
):

    if not youth_id:
        raise ValueError("Youth ID is required")

    if not opportunity_id:
        raise ValueError("Opportunity ID is required")

    with transaction() as db:

        youth = db.execute(
            "SELECT id, name FROM youth WHERE id = ?",
            (youth_id,)
        ).fetchone()

        if not youth:
            raise ValueError("Youth not found")

        opportunity = db.execute(
            "SELECT id, business_id, title, status FROM opportunities WHERE id = ?",
            (opportunity_id,)
        ).fetchone()

        if not opportunity:
            raise ValueError("Opportunity not found")

        existing = db.execute(
            "SELECT id FROM opportunity_matches WHERE youth_id = ? AND opportunity_id = ?",
            (youth_id, opportunity_id)
        ).fetchone()

        if existing:
            return existing["id"]

        match_id = generate_id("MATCH")
        created_at = utc_now()

        db.execute(
            """
            INSERT INTO opportunity_matches (
                id, youth_id, opportunity_id, match_score,
                reason, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (match_id, youth_id, opportunity_id, match_score, reason, "Pending", created_at)
        )

        db.execute(
            """
            INSERT INTO activity (
                id, event, actor_id, target_id, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "opportunity_matched",
                youth_id,
                opportunity_id,
                json.dumps({
                    "youth_id": youth_id,
                    "opportunity_id": opportunity_id,
                    "match_id": match_id,
                    "match_score": match_score,
                    "reason": reason
                }),
                created_at
            )
        )

    return match_id


def list_youth_matches(
    youth_id
):

    if not youth_id:
        raise ValueError("Youth ID is required")

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
            (youth_id,)
        ).fetchall()

    return [dict(row) for row in rows]
PYEOF

echo "Running tests..."
python -m pytest -q

echo ""
echo "Patch 1 complete: real match scoring engine + collision-safe IDs live."
