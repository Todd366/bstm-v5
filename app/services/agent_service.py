"""Field agents register people on their own phone and support them.

The agent never sees or chooses the person's real password: a temporary one is
shown once, and the person is asked to change it at first login."""

import secrets

from app.db.database import transaction
from app.services import youth_service

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def register_person(agent_key, agent_name, name, phone, location, goal, consent):
    if consent is not True:
        raise ValueError("Confirm that the person agreed to be registered")

    temp = "".join(secrets.choice(_ALPHABET) for _ in range(4)) + "-" + "".join(secrets.choice(_ALPHABET) for _ in range(4))
    youth_id = youth_service.create_youth(name, location, goal or "Find work", None, temp, phone=phone)

    with transaction() as db:
        db.execute("UPDATE youth SET registered_by = ?, must_change_password = true WHERE id = ?", (agent_key, youth_id))
        db.execute(
            "INSERT INTO activity (event, actor_id, target_id, details) VALUES ('registered_by_agent', NULL, ?, ?)",
            (youth_id, '{"agent": "%s"}' % str(agent_name).replace('"', "")),
        )

    return {"id": youth_id, "temporary_password": temp}


def my_people(agent_key=None):
    """An agent sees the people they registered; admins pass None to see all."""
    sql = ("SELECT id, name, phone, location, created_at, must_change_password, registered_by FROM youth "
           "WHERE deleted_at IS NULL AND registered_by IS NOT NULL")
    args = ()
    if agent_key:
        sql += " AND registered_by = ?"
        args = (agent_key,)
    with transaction() as db:
        rows = db.execute(sql + " ORDER BY created_at DESC LIMIT 200", args).fetchall()
    return [dict(r) for r in rows]
