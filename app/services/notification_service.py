"""In-app notifications. `notify` is called inside the caller's
transaction so a notification exists if and only if the event happened."""

from app.core.validation import clean_text, require_uuid
from app.db.database import transaction

RECIPIENTS = ("youth", "business")


def notify(db, recipient_type, recipient_id, kind, title, body=None):
    if recipient_type not in RECIPIENTS or not recipient_id:
        return

    db.execute(
        """
        INSERT INTO notifications (recipient_type, recipient_id, kind, title, body)
        VALUES (?, ?, ?, ?, ?)
        """,
        (recipient_type, recipient_id, kind, title[:200], (body or "")[:500] or None),
    )


def list_notifications(recipient_type, recipient_id, limit=30):
    recipient_id = require_uuid(recipient_id, "Account")
    limit = max(1, min(int(limit), 100))

    with transaction() as db:
        rows = db.execute(
            """
            SELECT id, kind, title, body, read_at, created_at
            FROM notifications
            WHERE recipient_type = ? AND recipient_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (recipient_type, recipient_id, limit),
        ).fetchall()

        unread = db.execute(
            """
            SELECT count(*) AS n FROM notifications
            WHERE recipient_type = ? AND recipient_id = ? AND read_at IS NULL
            """,
            (recipient_type, recipient_id),
        ).fetchone()["n"]

    return {"unread": unread, "items": [dict(r) for r in rows]}


def mark_all_read(recipient_type, recipient_id):
    recipient_id = require_uuid(recipient_id, "Account")

    with transaction() as db:
        db.execute(
            """
            UPDATE notifications SET read_at = now()
            WHERE recipient_type = ? AND recipient_id = ? AND read_at IS NULL
            """,
            (recipient_type, recipient_id),
        )

    return {"status": "ok"}
