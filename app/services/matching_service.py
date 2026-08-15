import json

import psycopg2.extras

from app.db.database import transaction


LEVEL_WEIGHTS = {
    "Beginner": 0,
    "Developing": 5,
    "Intermediate": 10,
    "Advanced": 15,
    "Expert": 20,
}


def calculate_match_score(
    capability_name,
    capability_category,
    level,
    verified,
    opportunity_title,
    opportunity_description,
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


def match_youth_to_opportunities(youth_id):
    """Known limitation carried over from the original design: this inner-
    joins businesses, so department-sourced opportunities (business_id is
    NULL) never appear here. Not fixed in this port — flagging for a
    follow-up slice rather than silently changing matching behavior."""

    if not youth_id:
        raise ValueError("Youth ID is required")

    with transaction() as db:

        youth = db.execute(
            "SELECT id, name FROM youth WHERE id = ?",
            (youth_id,),
        ).fetchone()

        if not youth:
            raise ValueError("Youth not found")

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
            (youth_id,),
        ).fetchall()

    results = [dict(row) for row in rows]

    for result in results:
        result["match_score"] = calculate_match_score(
            capability_name=result["capability_name"],
            capability_category=result["capability_category"],
            level=result["level"],
            verified=result["verified"],
            opportunity_title=result["title"],
            opportunity_description=result["description"],
        )

    results.sort(key=lambda r: r["match_score"], reverse=True)

    return results


def create_opportunity_match(youth_id, opportunity_id, match_score=0, reason=None):

    if not youth_id:
        raise ValueError("Youth ID is required")

    if not opportunity_id:
        raise ValueError("Opportunity ID is required")

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

        # reason is stored as jsonb — wrap non-null values so psycopg2
        # adapts them correctly (a plain string reason becomes a JSON string).
        reason_param = psycopg2.extras.Json(reason) if reason is not None else None

        row = db.execute(
            """
            INSERT INTO opportunity_matches (
                youth_id, opportunity_id, match_score, reason, status
            )
            VALUES (?, ?, ?, ?, 'Suggested')
            RETURNING id
            """,
            (youth_id, opportunity_id, match_score, reason_param),
        ).fetchone()

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
                        "youth_id": youth_id,
                        "opportunity_id": opportunity_id,
                        "match_id": str(match_id),
                        "match_score": match_score,
                    }
                ),
            ),
        )

    return str(match_id)


def list_youth_matches(youth_id):

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
            (youth_id,),
        ).fetchall()

    return [dict(row) for row in rows]
