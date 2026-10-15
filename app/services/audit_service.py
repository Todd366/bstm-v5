"""Field audits: structured on-site observations by BSTM field agents."""

import json

import psycopg2.extras

from app.core.validation import clean_text, require_uuid
from app.db.database import transaction

CHECKLIST = (
    "Customer traffic", "Staff and roles", "Products or services",
    "Technology in use", "Marketing and branding", "Cleanliness and organisation",
)
RATINGS = ("G", "F", "P")


def create_field_audit(data, auditor="staff"):
    name = clean_text(data.get("business_name"), "Business name", 150)
    location = clean_text(data.get("location"), "Location", 120)
    insight = clean_text(data.get("insight"), "Insight", 1000, required=False)

    business_id = data.get("business_id")
    business_id = require_uuid(business_id, "Business") if business_id else None

    ratings = data.get("ratings") or {}
    if not isinstance(ratings, dict):
        raise ValueError("Ratings must be an object")
    ratings = {k: v for k, v in ratings.items() if k in CHECKLIST and v in RATINGS}

    rooms = sorted({int(r) for r in (data.get("rooms") or [])})
    if any(r < 1 or r > 63 for r in rooms):
        raise ValueError("Rooms must be between 1 and 63")

    try:
        score = int(data.get("score", 5))
    except (TypeError, ValueError):
        raise ValueError("Score must be a number from 1 to 10")
    if not 1 <= score <= 10:
        raise ValueError("Score must be a number from 1 to 10")

    with transaction() as db:
        if business_id:
            if not db.execute("SELECT 1 FROM businesses WHERE id = ?", (business_id,)).fetchone():
                raise ValueError("Business not found")

        row = db.execute(
            """
            INSERT INTO field_audits
                (business_id, business_name, location, ratings, rooms, insight, score, auditor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (business_id, name, location, psycopg2.extras.Json(ratings), "{" + ",".join(str(r) for r in rooms) + "}", insight, score, auditor),
        ).fetchone()

        if business_id:
            db.execute(
                "UPDATE businesses SET audit_status = 'Completed', updated_at = now() WHERE id = ?",
                (business_id,),
            )

        db.execute(
            "INSERT INTO activity (event, actor_id, target_id, details) VALUES (?, ?, ?, ?)",
            ("field_audit_recorded", business_id, row["id"], json.dumps({"score": score, "rooms": rooms})),
        )

    return str(row["id"])


def list_field_audits(limit=50, offset=0):
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    with transaction() as db:
        rows = db.execute(
            """
            SELECT id, business_id, business_name, location, ratings, rooms,
                   insight, score, auditor, created_at
            FROM field_audits ORDER BY created_at DESC LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]
