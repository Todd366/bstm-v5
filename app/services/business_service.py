import json

from app.core.ids import generate_id
from app.core.time import utc_now
from app.db.database import transaction


def create_business(
    name,
    owner,
    sector,
    location,
    main_problem
):

    business_id = generate_id(
        "B"
    )

    with transaction() as db:

        existing = db.execute(
            """
            SELECT id
            FROM businesses
            WHERE name = ? COLLATE NOCASE
            """,
            (
                name.strip(),
            )
        ).fetchone()

        if existing:

            raise ValueError(
                "Business already exists"
            )

        db.execute(
            """
            INSERT INTO businesses (
                id,
                name,
                owner,
                sector,
                location,
                main_problem,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                name.strip(),
                owner.strip(),
                sector.strip(),
                location.strip(),
                main_problem.strip(),
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
                "business_activated",
                business_id,
                business_id,
                json.dumps({
                    "name": name,
                    "sector": sector
                }),
                utc_now()
            )
        )

    return business_id
