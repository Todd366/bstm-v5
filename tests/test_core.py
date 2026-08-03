import os
import tempfile

import app.core.config as config
import app.db.database as database


def test_database_initialization():

    original = config.DATABASE_PATH

    temp = tempfile.NamedTemporaryFile(
        delete=False
    )

    temp.close()

    config.DATABASE_PATH = temp.name
    database.DATABASE_PATH = temp.name

    try:

        database.initialize_database()

        with database.get_connection() as db:

            result = db.execute(
                "SELECT 1"
            ).fetchone()

            assert result[0] == 1

    finally:

        config.DATABASE_PATH = original

        database.DATABASE_PATH = original

        os.unlink(
            temp.name
        )
