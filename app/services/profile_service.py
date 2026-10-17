"""Youth profile editing and the opt-in public profile.

A public profile is OFF by default. When on, it shows only: name,
town, level, bio, member-since, counts, and skills — with declared
skills kept separate from staff-verified ones (a stated skill is not a
verified credential). Never email, intake answers, money or evidence."""

import json

from app.core.validation import clean_text, require_uuid
from app.db.database import transaction


def update_profile(youth_id, data):
    youth_id = require_uuid(youth_id, "Youth")

    bio = clean_text(data.get("bio"), "Bio", 500, required=False)
    location = clean_text(data.get("location"), "Location", 120)
    availability = clean_text(data.get("availability"), "Availability", 100, required=False)
    equipment = clean_text(data.get("equipment"), "Equipment", 300, required=False)
    passion = clean_text(data.get("passion"), "Passion", 300, required=False)
    public_profile = bool(data.get("public_profile"))

    with transaction() as db:
        row = db.execute(
            """
            UPDATE youth
            SET bio = ?, location = ?, availability = ?, equipment = ?, passion = ?,
                public_profile = ?, updated_at = now()
            WHERE id = ? RETURNING id
            """,
            (bio, location, availability, equipment, passion, public_profile, youth_id),
        ).fetchone()

        if not row:
            raise ValueError("Youth not found")

        db.execute(
            "INSERT INTO activity (event, actor_id, target_id, details) VALUES (?, ?, ?, ?)",
            ("profile_updated", youth_id, youth_id, json.dumps({"public_profile": public_profile})),
        )

    return {"status": "saved"}


def get_public_profile(youth_id):
    youth_id = require_uuid(youth_id, "Profile")

    with transaction() as db:

        youth = db.execute(
            """
            SELECT id, name, location, level, bio, completed_trials,
                   completed_opportunities, created_at
            FROM youth WHERE id = ? AND public_profile
            """,
            (youth_id,),
        ).fetchone()

        if not youth:
            # Same answer for "no such person" and "profile is private".
            raise ValueError("Profile not found")

        skills = db.execute(
            """
            SELECT c.name, c.category, yc.level, yc.verified
            FROM youth_capabilities yc JOIN capabilities c ON c.id = yc.capability_id
            WHERE yc.youth_id = ?
            ORDER BY yc.verified DESC, c.name
            """,
            (youth_id,),
        ).fetchall()

    skills = [dict(s) for s in skills]

    return {
        "name": youth["name"],
        "location": youth["location"],
        "level": youth["level"],
        "bio": youth["bio"],
        "member_since": youth["created_at"],
        "completed_trials": youth["completed_trials"],
        "completed_jobs": youth["completed_opportunities"],
        "verified_skills": [s for s in skills if s["verified"]],
        "declared_skills": [s for s in skills if not s["verified"]],
    }
