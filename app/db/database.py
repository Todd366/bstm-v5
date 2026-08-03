import sqlite3
from contextlib import contextmanager

from app.core.config import DATABASE_PATH


def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = (
        sqlite3.Row
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


@contextmanager
def transaction():

    connection = get_connection()

    try:

        yield connection

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


def initialize_database():

    with transaction() as db:

        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS youth (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                passion TEXT NOT NULL,
                skills TEXT,
                goal TEXT NOT NULL,
                availability TEXT,
                equipment TEXT,
                level TEXT NOT NULL DEFAULT 'Explorer',
                capability_score INTEGER NOT NULL DEFAULT 0,
                learning_score INTEGER NOT NULL DEFAULT 0,
                reputation_score REAL NOT NULL DEFAULT 50,
                reliability_score REAL NOT NULL DEFAULT 50,
                completed_trials INTEGER NOT NULL DEFAULT 0,
                completed_opportunities INTEGER NOT NULL DEFAULT 0,
                revenue REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_youth_name
            ON youth(name COLLATE NOCASE);


            CREATE TABLE IF NOT EXISTS businesses (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                sector TEXT NOT NULL,
                location TEXT NOT NULL,
                main_problem TEXT NOT NULL,
                audit_status TEXT NOT NULL DEFAULT 'Pending',
                opportunities_generated INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_business_name
            ON businesses(name COLLATE NOCASE);


            CREATE TABLE IF NOT EXISTS activity (
                id TEXT PRIMARY KEY,
                event TEXT NOT NULL,
                actor_id TEXT,
                target_id TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                business_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS trials (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL,
                youth_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Proposed',
                created_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                youth_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Suggested',
                created_at TEXT NOT NULL
            );
            """
        )

    ensure_slice2_schema()

    ensure_slice3a_schema()

    ensure_slice3b_schema()

    ensure_slice4_schema()

def ensure_slice2_schema():

    with get_connection() as db:

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS capabilities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS youth_capabilities (
                id TEXT PRIMARY KEY,
                youth_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                level TEXT NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(youth_id, capability_id),
                FOREIGN KEY(youth_id)
                    REFERENCES youth(id),
                FOREIGN KEY(capability_id)
                    REFERENCES capabilities(id)
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunity_matches (
                id TEXT PRIMARY KEY,
                youth_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                match_score REAL NOT NULL DEFAULT 0,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                UNIQUE(youth_id, opportunity_id),
                FOREIGN KEY(youth_id)
                    REFERENCES youth(id),
                FOREIGN KEY(opportunity_id)
                    REFERENCES opportunities(id)
            )
            """
        )

        db.commit()


def ensure_slice3a_schema():

    with get_connection() as db:

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunity_assignments (
                id TEXT PRIMARY KEY,
                youth_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                match_id TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                assigned_at TEXT NOT NULL,
                accepted_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(youth_id, opportunity_id),
                FOREIGN KEY(youth_id)
                    REFERENCES youth(id),
                FOREIGN KEY(opportunity_id)
                    REFERENCES opportunities(id),
                FOREIGN KEY(match_id)
                    REFERENCES opportunity_matches(id)
            )
            """
        )

        db.commit()


def ensure_slice3b_schema():

    with get_connection() as db:

        # Slice 3B must work with databases created by
        # earlier BSTM V5 versions. CREATE TABLE IF NOT EXISTS
        # alone cannot upgrade an existing trials table.

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS trials (
                id TEXT PRIMARY KEY,
                assignment_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                youth_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'Created',
                submission TEXT,
                review TEXT,
                cancellation_reason TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                submitted_at TEXT,
                reviewed_at TEXT,
                completed_at TEXT,
                cancelled_at TEXT,
                UNIQUE(assignment_id),
                FOREIGN KEY(assignment_id)
                    REFERENCES opportunity_assignments(id),
                FOREIGN KEY(opportunity_id)
                    REFERENCES opportunities(id),
                FOREIGN KEY(youth_id)
                    REFERENCES youth(id)
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in db.execute(
                """
                PRAGMA table_info(trials)
                """
            ).fetchall()
        }

        required_columns = {
            "assignment_id": "TEXT",
            "opportunity_id": "TEXT",
            "youth_id": "TEXT",
            "title": "TEXT",
            "description": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'Created'",
            "submission": "TEXT",
            "review": "TEXT",
            "cancellation_reason": "TEXT",
            "created_at": "TEXT",
            "started_at": "TEXT",
            "submitted_at": "TEXT",
            "reviewed_at": "TEXT",
            "completed_at": "TEXT",
            "cancelled_at": "TEXT"
        }

        for column, definition in required_columns.items():

            if column not in existing_columns:

                # SQLite ALTER TABLE supports adding columns,
                # but NOT adding new foreign keys or UNIQUE constraints.
                # Those constraints are handled by the service layer
                # and the new-table definition above.

                db.execute(
                    f"""
                    ALTER TABLE trials
                    ADD COLUMN {column} {definition}
                    """
                )

        # Migrate legacy Slice 1 trial records where possible.
        #
        # Legacy rows have opportunity_id and youth_id but no assignment_id.
        # We only link them when exactly one assignment exists for that
        # youth/opportunity pair.

        db.execute(
            """
            UPDATE trials
            SET assignment_id = (
                SELECT oa.id
                FROM opportunity_assignments oa
                WHERE oa.youth_id = trials.youth_id
                  AND oa.opportunity_id = trials.opportunity_id
                LIMIT 1
            )
            WHERE assignment_id IS NULL
              AND opportunity_id IS NOT NULL
              AND youth_id IS NOT NULL
            """
        )

        # Provide safe defaults for legacy rows.
        db.execute(
            """
            UPDATE trials
            SET title = COALESCE(
                NULLIF(title, ''),
                'Legacy Trial'
            )
            WHERE title IS NULL
               OR title = ''
            """
        )

        db.execute(
            """
            UPDATE trials
            SET status = 'Created'
            WHERE status IS NULL
               OR status = ''
               OR status = 'Proposed'
            """
        )

        db.commit()


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
