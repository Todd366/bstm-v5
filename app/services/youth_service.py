import json

from app.core.ids import generate_id
from app.core.time import utc_now
from app.db.database import transaction


def create_youth(
    name,
    location,
    passion,
    goal,
    skills=None,
    availability=None,
    equipment=None
):

    youth_id = generate_id(
        "Y"
    )

    with transaction() as db:

        existing = db.execute(
            """
            SELECT id
            FROM youth
            WHERE name = ? COLLATE NOCASE
            """,
            (
                name.strip(),
            )
        ).fetchone()

        if existing:

            raise ValueError(
                "Youth profile already exists"
            )

        db.execute(
            """
            INSERT INTO youth (
                id,
                name,
                location,
                passion,
                skills,
                goal,
                availability,
                equipment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                youth_id,
                name.strip(),
                location.strip(),
                passion.strip(),
                skills,
                goal.strip(),
                availability,
                equipment,
                utc_now()
            )
        )

        db.execute(
            """
            INSERT INTO activity (
                id,
                event,
                actor_id,
                target_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "youth_activated",
                youth_id,
                youth_id,
                json.dumps({
                    "name": name,
                    "location": location
                }),
                utc_now()
            )
        )

    return youth_id
