#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/bstm-activation/bstm_v5

echo "Backing up..."
cp bstm.db "bstm_pre_patch2_$(date +%Y%m%d_%H%M%S).db" 2>/dev/null || true

echo "Adding department registry..."
cat << 'PYEOF' > app/core/departments.py
DEPARTMENTS = [
    "AI & Machine Learning",
    "Trading Automation",
    "VPN & Network Security",
    "Web Development",
    "Mobile Applications",
    "System Integration & API",
    "Data Science & Analytics",
    "Blockchain & Cryptocurrency",
    "Graphic Design & Branding",
    "Content Creation & Copywriting",
    "Social Media Management",
    "Digital Marketing & Advertising",
    "BSTM Tutorial Center",
    "Private Security",
    "Music",
    "CabLink Transportation",
    "Finance & Accounting",
    "Marketplace & E-Commerce",
    "Research & Development",
    "Healthcare Information & Wellness",
    "Nutrition & Health Products",
    "Micro Farming & Urban Agriculture",
    "Sustainability & Environment",
    "Human Resources & Talent Development",
    "Project Management Office",
    "Legal & Compliance",
    "G.I.N - Global Intelligence Network",
    "BSTM Clothing Brand",
    "Spiritual Guidance & Consciousness",
    "BHD - Black Hole Drive"
]
PYEOF

echo "Adding department + budget columns to opportunities (migration)..."
cat << 'PYEOF' >> app/db/database.py


def ensure_slice4_schema():

    with get_connection() as db:

        existing_columns = {
            row["name"]
            for row in db.execute(
                """
                PRAGMA table_info(opportunities)
                """
            ).fetchall()
        }

        if "department" not in existing_columns:

            db.execute(
                """
                ALTER TABLE opportunities
                ADD COLUMN department TEXT
                """
            )

        if "budget" not in existing_columns:

            db.execute(
                """
                ALTER TABLE opportunities
                ADD COLUMN budget REAL NOT NULL DEFAULT 0
                """
            )

        db.commit()
PYEOF

python - <<'PY'
import re

path = "app/db/database.py"

with open(path) as f:
    content = f.read()

content = content.replace(
    "    ensure_slice3a_schema()\n\n    ensure_slice3b_schema()",
    "    ensure_slice3a_schema()\n\n    ensure_slice3b_schema()\n\n    ensure_slice4_schema()"
)

with open(path, "w") as f:
    f.write(content)
PY

echo "Updating opportunity_service.py (department + budget on create)..."
cat << 'PYEOF' > app/services/opportunity_service.py
import json

from app.core.departments import DEPARTMENTS
from app.core.ids import generate_id
from app.core.time import utc_now
from app.db.database import transaction


def create_opportunity(
    business_id,
    title,
    description=None,
    department=None,
    budget=0
):

    if not business_id:
        raise ValueError("Business ID is required")

    if not title or not title.strip():
        raise ValueError("Opportunity title is required")

    if department is not None and department not in DEPARTMENTS:
        raise ValueError("Invalid department")

    if budget is None:
        budget = 0

    if budget < 0:
        raise ValueError("Budget cannot be negative")

    with transaction() as db:

        business = db.execute(
            "SELECT id, name FROM businesses WHERE id = ?",
            (business_id,)
        ).fetchone()

        if not business:
            raise ValueError("Business not found")

        opportunity_id = generate_id("OP")
        created_at = utc_now()

        db.execute(
            """
            INSERT INTO opportunities (
                id, business_id, title, description,
                status, department, budget, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                business_id,
                title.strip(),
                description.strip() if description else None,
                "Open",
                department,
                budget,
                created_at
            )
        )

        db.execute(
            """
            UPDATE businesses
            SET opportunities_generated = opportunities_generated + 1
            WHERE id = ?
            """,
            (business_id,)
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
                "opportunity_created",
                business_id,
                opportunity_id,
                json.dumps({
                    "business_id": business_id,
                    "business_name": business["name"],
                    "title": title.strip(),
                    "department": department,
                    "budget": budget
                }),
                created_at
            )
        )

    return opportunity_id


def list_opportunities():

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                o.id, o.business_id, b.name AS business_name,
                o.title, o.description, o.status,
                o.department, o.budget, o.created_at
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            ORDER BY o.created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_opportunity(
    opportunity_id
):

    if not opportunity_id:
        raise ValueError("Opportunity ID is required")

    with transaction() as db:

        row = db.execute(
            """
            SELECT
                o.id, o.business_id, b.name AS business_name,
                o.title, o.description, o.status,
                o.department, o.budget, o.created_at
            FROM opportunities o
            LEFT JOIN businesses b ON b.id = o.business_id
            WHERE o.id = ?
            """,
            (opportunity_id,)
        ).fetchone()

    if not row:
        raise ValueError("Opportunity not found")

    return dict(row)
PYEOF

echo "Wiring revenue distribution into complete_assignment..."
cat << 'PYEOF' > app/services/assignment_service.py
import json

from app.core.ids import generate_id
from app.core.time import utc_now
from app.db.database import transaction


VALID_STATUSES = [
    "Pending",
    "Accepted",
    "Declined",
    "Cancelled",
    "Completed"
]

YOUTH_REVENUE_SHARE = 0.70


def create_assignment(
    youth_id,
    opportunity_id,
    match_id=None
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
            "SELECT id, business_id, title, description, status FROM opportunities WHERE id = ?",
            (opportunity_id,)
        ).fetchone()

        if not opportunity:
            raise ValueError("Opportunity not found")

        if opportunity["status"] != "Open":
            raise ValueError("Opportunity is not open")

        if match_id:

            match = db.execute(
                "SELECT id, youth_id, opportunity_id FROM opportunity_matches WHERE id = ?",
                (match_id,)
            ).fetchone()

            if not match:
                raise ValueError("Opportunity match not found")

            if match["youth_id"] != youth_id:
                raise ValueError("Match does not belong to youth")

            if match["opportunity_id"] != opportunity_id:
                raise ValueError("Match does not belong to opportunity")

        existing = db.execute(
            "SELECT id, status FROM opportunity_assignments WHERE youth_id = ? AND opportunity_id = ?",
            (youth_id, opportunity_id)
        ).fetchone()

        if existing:
            raise ValueError("Assignment already exists")

        assignment_id = generate_id("ASSIGN")
        created_at = utc_now()

        db.execute(
            """
            INSERT INTO opportunity_assignments (
                id, youth_id, opportunity_id, match_id,
                status, assigned_at, accepted_at, completed_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (assignment_id, youth_id, opportunity_id, match_id, "Pending", created_at, None, None, created_at)
        )

        db.execute(
            """
            INSERT INTO activity (id, event, actor_id, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "opportunity_assigned",
                youth_id,
                assignment_id,
                json.dumps({
                    "assignment_id": assignment_id,
                    "youth_id": youth_id,
                    "youth_name": youth["name"],
                    "opportunity_id": opportunity_id,
                    "opportunity_title": opportunity["title"],
                    "match_id": match_id,
                    "status": "Pending"
                }),
                created_at
            )
        )

    return assignment_id


def accept_assignment(
    assignment_id
):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT oa.id, oa.youth_id, oa.opportunity_id, oa.status,
                   y.name AS youth_name, o.title AS opportunity_title
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,)
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] != "Pending":
            raise ValueError("Only pending assignments can be accepted")

        accepted_at = utc_now()

        db.execute(
            "UPDATE opportunity_assignments SET status = ?, accepted_at = ? WHERE id = ?",
            ("Accepted", accepted_at, assignment_id)
        )

        db.execute(
            """
            INSERT INTO activity (id, event, actor_id, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "assignment_accepted",
                assignment["youth_id"],
                assignment_id,
                json.dumps({
                    "assignment_id": assignment_id,
                    "youth_id": assignment["youth_id"],
                    "youth_name": assignment["youth_name"],
                    "opportunity_id": assignment["opportunity_id"],
                    "opportunity_title": assignment["opportunity_title"],
                    "status": "Accepted"
                }),
                accepted_at
            )
        )

    return assignment_id


def decline_assignment(
    assignment_id
):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT oa.id, oa.youth_id, oa.opportunity_id, oa.status,
                   y.name AS youth_name, o.title AS opportunity_title
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,)
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] != "Pending":
            raise ValueError("Only pending assignments can be declined")

        declined_at = utc_now()

        db.execute(
            "UPDATE opportunity_assignments SET status = ? WHERE id = ?",
            ("Declined", assignment_id)
        )

        db.execute(
            """
            INSERT INTO activity (id, event, actor_id, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "assignment_declined",
                assignment["youth_id"],
                assignment_id,
                json.dumps({
                    "assignment_id": assignment_id,
                    "youth_id": assignment["youth_id"],
                    "youth_name": assignment["youth_name"],
                    "opportunity_id": assignment["opportunity_id"],
                    "opportunity_title": assignment["opportunity_title"],
                    "status": "Declined"
                }),
                declined_at
            )
        )

    return assignment_id


def cancel_assignment(
    assignment_id
):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            "SELECT id, youth_id, opportunity_id, status FROM opportunity_assignments WHERE id = ?",
            (assignment_id,)
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] in ["Completed", "Cancelled", "Declined"]:
            raise ValueError("Assignment cannot be cancelled")

        cancelled_at = utc_now()

        db.execute(
            "UPDATE opportunity_assignments SET status = ? WHERE id = ?",
            ("Cancelled", assignment_id)
        )

        db.execute(
            """
            INSERT INTO activity (id, event, actor_id, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "assignment_cancelled",
                assignment["youth_id"],
                assignment_id,
                json.dumps({
                    "assignment_id": assignment_id,
                    "youth_id": assignment["youth_id"],
                    "opportunity_id": assignment["opportunity_id"],
                    "status": "Cancelled"
                }),
                cancelled_at
            )
        )

    return assignment_id


def complete_assignment(
    assignment_id
):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        assignment = db.execute(
            """
            SELECT oa.id, oa.youth_id, oa.opportunity_id, oa.status, o.budget
            FROM opportunity_assignments oa
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,)
        ).fetchone()

        if not assignment:
            raise ValueError("Assignment not found")

        if assignment["status"] != "Accepted":
            raise ValueError("Only accepted assignments can be completed")

        completed_at = utc_now()

        db.execute(
            "UPDATE opportunity_assignments SET status = ?, completed_at = ? WHERE id = ?",
            ("Completed", completed_at, assignment_id)
        )

        db.execute(
            "UPDATE youth SET completed_opportunities = completed_opportunities + 1 WHERE id = ?",
            (assignment["youth_id"],)
        )

        budget = assignment["budget"] or 0
        youth_share = round(budget * YOUTH_REVENUE_SHARE, 2)
        ecosystem_share = round(budget - youth_share, 2)

        if budget > 0:

            db.execute(
                "UPDATE youth SET revenue = revenue + ? WHERE id = ?",
                (youth_share, assignment["youth_id"])
            )

            db.execute(
                """
                INSERT INTO activity (id, event, actor_id, target_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    generate_id("EV"),
                    "revenue_distributed",
                    assignment["youth_id"],
                    assignment_id,
                    json.dumps({
                        "assignment_id": assignment_id,
                        "youth_id": assignment["youth_id"],
                        "opportunity_id": assignment["opportunity_id"],
                        "budget": budget,
                        "youth_share": youth_share,
                        "ecosystem_share": ecosystem_share
                    }),
                    completed_at
                )
            )

        db.execute(
            """
            INSERT INTO activity (id, event, actor_id, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id("EV"),
                "assignment_completed",
                assignment["youth_id"],
                assignment_id,
                json.dumps({
                    "assignment_id": assignment_id,
                    "youth_id": assignment["youth_id"],
                    "opportunity_id": assignment["opportunity_id"],
                    "status": "Completed"
                }),
                completed_at
            )
        )

    return assignment_id


def get_assignment(
    assignment_id
):

    if not assignment_id:
        raise ValueError("Assignment ID is required")

    with transaction() as db:

        row = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, y.name AS youth_name,
                   oa.opportunity_id, o.title AS opportunity_title,
                   o.description AS opportunity_description, o.business_id,
                   oa.match_id, oa.status, oa.assigned_at, oa.accepted_at,
                   oa.completed_at, oa.created_at
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.id = ?
            """,
            (assignment_id,)
        ).fetchone()

    if not row:
        raise ValueError("Assignment not found")

    return dict(row)


def list_youth_assignments(
    youth_id
):

    if not youth_id:
        raise ValueError("Youth ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, oa.opportunity_id,
                   o.title AS opportunity_title, o.description AS opportunity_description,
                   o.business_id, oa.match_id, oa.status, oa.assigned_at,
                   oa.accepted_at, oa.completed_at, oa.created_at
            FROM opportunity_assignments oa
            JOIN opportunities o ON o.id = oa.opportunity_id
            WHERE oa.youth_id = ?
            ORDER BY oa.created_at DESC
            """,
            (youth_id,)
        ).fetchall()

    return [dict(row) for row in rows]


def list_opportunity_assignments(
    opportunity_id
):

    if not opportunity_id:
        raise ValueError("Opportunity ID is required")

    with transaction() as db:

        rows = db.execute(
            """
            SELECT oa.id AS assignment_id, oa.youth_id, y.name AS youth_name,
                   oa.opportunity_id, oa.match_id, oa.status, oa.assigned_at,
                   oa.accepted_at, oa.completed_at, oa.created_at
            FROM opportunity_assignments oa
            JOIN youth y ON y.id = oa.youth_id
            WHERE oa.opportunity_id = ?
            ORDER BY oa.created_at DESC
            """,
            (opportunity_id,)
        ).fetchall()

    return [dict(row) for row in rows]
PYEOF

echo "Running tests..."
python -m pytest -q

echo ""
echo "Patch 2 complete: departments + budgets on opportunities, revenue auto-distributed on assignment completion (70/30 split, logged in activity)."
