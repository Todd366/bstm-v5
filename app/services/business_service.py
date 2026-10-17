import json

import psycopg2

from app.core.errors import Conflict
from app.core.config import RATE_LOGIN_PER_15MIN_ACCOUNT
from app.core.validation import clean_email, clean_text, require_uuid
from app.db.database import transaction
from app.services.auth_service import (
    burn_verification_time,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from app.services.rate_limit_service import check_rate_limit, hash_key

# Never `SELECT *`: password_hash must not leave this module.
_COLUMNS = """
    id, name, owner, sector, location, main_problem, audit_status,
    opportunities_generated, email, phone, created_at, updated_at
"""


def create_business(
    name,
    owner,
    sector,
    location,
    main_problem,
    email=None,
    phone=None,
    password=None,
):
    """Creates a business profile. Returns the new business's UUID (str).

    A business is identified by name + location (two shops can share a
    name in different villages)."""

    name = clean_text(name, "Business name", 150)
    owner = clean_text(owner, "Owner", 120)
    sector = clean_text(sector, "Sector", 100)
    location = clean_text(location, "Location", 120)
    main_problem = clean_text(main_problem, "Main problem", 1000)
    phone = clean_text(phone, "Phone", 30, required=False)
    password_hash = None

    if password:
        email = clean_email(email)
        validate_password(password)
        password_hash = hash_password(password)
    elif email:
        email = clean_email(email)

    try:
        with transaction() as db:

            existing = db.execute(
                """
                SELECT id
                FROM businesses
                WHERE lower(name) = lower(?) AND lower(location) = lower(?)
                """,
                (name, location),
            ).fetchone()

            if existing:
                raise Conflict("This business is already registered at that location")

            row = db.execute(
                """
                INSERT INTO businesses (
                    name, owner, sector, location, main_problem,
                    email, phone, password_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (name, owner, sector, location, main_problem, email, phone, password_hash),
            ).fetchone()

            business_id = row["id"]

            db.execute(
                """
                INSERT INTO activity (event, actor_id, target_id, details)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "business_activated",
                    business_id,
                    business_id,
                    json.dumps({"sector": sector, "location": location}),
                ),
            )

    except psycopg2.errors.UniqueViolation:
        raise Conflict("This business or email is already registered")

    return str(business_id)


def get_business(business_id):

    business_id = require_uuid(business_id, "Business")

    with transaction() as db:

        row = db.execute(
            f"SELECT {_COLUMNS} FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

    if not row:
        raise ValueError("Business not found")

    return dict(row)


def list_businesses(limit=50, offset=0):

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    with transaction() as db:

        rows = db.execute(
            f"""
            SELECT {_COLUMNS} FROM businesses
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]


def set_audit_status(business_id, status):

    business_id = require_uuid(business_id, "Business")

    if status not in ("Pending", "InProgress", "Completed"):
        raise ValueError(f"Invalid audit_status: {status}")

    with transaction() as db:

        row = db.execute(
            """
            UPDATE businesses
            SET audit_status = ?, updated_at = now()
            WHERE id = ?
            RETURNING id
            """,
            (status, business_id),
        ).fetchone()

        if not row:
            raise ValueError("Business not found")

        db.execute(
            """
            INSERT INTO activity (event, actor_id, target_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                "business_audit_status",
                business_id,
                business_id,
                json.dumps({"status": status}),
            ),
        )

    return get_business(business_id)


def authenticate_business(email, password):
    """Same guarantees as authenticate_youth: one error message, equal
    CPU cost, per-account throttle."""

    if not isinstance(email, str) or not isinstance(password, str):
        raise ValueError("Invalid email or password")

    email = email.strip()

    if not email or not password or len(password) > 128 or len(email) > 254:
        raise ValueError("Invalid email or password")

    check_rate_limit(hash_key("biz:" + email.lower()), "login-account", RATE_LOGIN_PER_15MIN_ACCOUNT, 15)

    with transaction() as db:

        row = db.execute(
            "SELECT id, password_hash FROM businesses WHERE lower(email) = lower(?)",
            (email,),
        ).fetchone()

        if not row or not row["password_hash"]:
            burn_verification_time(password)
            raise ValueError("Invalid email or password")

        if not verify_password(password, row["password_hash"]):
            raise ValueError("Invalid email or password")

        if needs_rehash(row["password_hash"]):
            db.execute(
                "UPDATE businesses SET password_hash = ? WHERE id = ?",
                (hash_password(password), row["id"]),
            )

    return str(row["id"])


def list_own_opportunities(business_id):
    business_id = require_uuid(business_id, "Business")

    with transaction() as db:
        rows = db.execute(
            """
            SELECT o.id, o.title, o.description, o.department, o.budget, o.status,
                   o.approval_status, o.created_at,
                   (SELECT count(*) FROM opportunity_assignments oa
                    WHERE oa.opportunity_id = o.id AND oa.status IN ('Pending', 'Accepted', 'Completed')) AS people
            FROM opportunities o
            WHERE o.business_id = ?
            ORDER BY o.created_at DESC LIMIT 100
            """,
            (business_id,),
        ).fetchall()

    return [dict(r) for r in rows]


def list_own_applicants(business_id, opportunity_id):
    """People on one of THIS business's jobs, with the state of their
    work. Ownership is checked in the query; another business's job id
    reports 'not found'."""

    business_id = require_uuid(business_id, "Business")
    opportunity_id = require_uuid(opportunity_id, "Opportunity")

    with transaction() as db:

        owned = db.execute(
            "SELECT status FROM opportunities WHERE id = ? AND business_id = ?",
            (opportunity_id, business_id),
        ).fetchone()

        if not owned:
            raise ValueError("Opportunity not found")

        rows = db.execute(
            """
            SELECT oa.id AS assignment_id, y.name, y.location, y.level, oa.status, oa.created_at,
                   t.id AS trial_id, t.status AS trial_status, t.submission,
                   (SELECT count(*) FROM youth_capabilities yc
                    WHERE yc.youth_id = y.id AND yc.verified) AS verified_skills
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            LEFT JOIN LATERAL (
                SELECT id, status, submission FROM trials
                WHERE assignment_id = oa.id AND status <> 'Cancelled'
                ORDER BY created_at DESC LIMIT 1
            ) t ON true
            WHERE oa.opportunity_id = ?
            ORDER BY oa.created_at DESC
            """,
            (opportunity_id,),
        ).fetchall()

    return [dict(r, opportunity_status=owned["status"]) for r in rows]


def accept_applicant(business_id, assignment_id):
    """The business picks one applicant for its own job."""

    from app.services.assignment_service import accept_assignment

    return accept_assignment(assignment_id, acting_business_id=require_uuid(business_id, "Business"))


def decline_applicant(business_id, assignment_id):
    from app.services.assignment_service import decline_assignment

    return decline_assignment(assignment_id, acting_business_id=require_uuid(business_id, "Business"))


def close_own_job(business_id, opportunity_id):
    from app.services.opportunity_service import close_opportunity

    business_id = require_uuid(business_id, "Business")
    opportunity_id = require_uuid(opportunity_id, "Opportunity")

    with transaction() as db:
        owned = db.execute(
            "SELECT 1 FROM opportunities WHERE id = ? AND business_id = ?",
            (opportunity_id, business_id),
        ).fetchone()

    if not owned:
        raise ValueError("Opportunity not found")

    return close_opportunity(opportunity_id)


def approve_work(business_id, trial_id, score, note=None):
    """The business confirms the work on its own job was done. Approving
    completes the trial, the job and issues the invoice."""

    from app.services.trial_service import complete_trial, review_trial

    business_id = require_uuid(business_id, "Business")
    trial_id = require_uuid(trial_id, "Trial")
    note = clean_text(note, "Note", 500, required=False)

    try:
        score = float(score)
    except (TypeError, ValueError):
        raise ValueError("Score must be a number from 0 to 100")

    if not 0 <= score <= 100:
        raise ValueError("Score must be a number from 0 to 100")

    with transaction() as db:
        trial = db.execute(
            """
            SELECT t.status FROM trials t
            JOIN opportunity_assignments oa ON oa.id = t.assignment_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE t.id = ? AND o.business_id = ?
            """,
            (trial_id, business_id),
        ).fetchone()

    if not trial:
        raise ValueError("Trial not found")

    if trial["status"] not in ("Submitted", "Under Review"):
        raise Conflict("This work is not waiting for approval")

    if trial["status"] == "Submitted":
        review_trial(trial_id, {"by": "business"})

    complete_trial(trial_id, {"score": score, "note": note, "by": "business"})

    return trial_id
