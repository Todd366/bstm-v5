import os
import tempfile

import pytest

import app.core.config as config
import app.db.database as database

from app.services.business_service import (
    create_business
)

from app.services.opportunity_service import (
    create_opportunity,
    get_opportunity,
    list_opportunities
)


@pytest.fixture
def test_database():

    original_path = config.DATABASE_PATH

    temp = tempfile.NamedTemporaryFile(
        delete=False
    )

    temp.close()

    config.DATABASE_PATH = temp.name
    database.DATABASE_PATH = temp.name

    database.initialize_database()

    try:

        yield

    finally:

        config.DATABASE_PATH = original_path
        database.DATABASE_PATH = original_path

        if os.path.exists(
            temp.name
        ):
            os.unlink(
                temp.name
            )


def test_create_opportunity_for_existing_business(
    test_database
):

    business_id = create_business(
        name="Test Business",
        owner="Test Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="No digital presence"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Digital Presence Setup",
        description="Create a basic digital presence."
    )

    assert opportunity_id.startswith(
        "OP-"
    )

    opportunity = get_opportunity(
        opportunity_id
    )

    assert opportunity["id"] == opportunity_id

    assert opportunity["business_id"] == business_id

    assert opportunity["business_name"] == "Test Business"

    assert opportunity["title"] == (
        "Digital Presence Setup"
    )

    assert opportunity["status"] == "Open"


def test_opportunity_updates_business_counter(
    test_database
):

    business_id = create_business(
        name="Counter Business",
        owner="Owner",
        sector="Retail",
        location="Mopane",
        main_problem="Weak marketing"
    )

    create_opportunity(
        business_id=business_id,
        title="Marketing Opportunity"
    )

    with database.get_connection() as db:

        row = db.execute(
            """
            SELECT opportunities_generated
            FROM businesses
            WHERE id = ?
            """,
            (
                business_id,
            )
        ).fetchone()

    assert row[0] == 1


def test_opportunity_creates_activity_event(
    test_database
):

    business_id = create_business(
        name="Activity Business",
        owner="Owner",
        sector="Services",
        location="Gaborone",
        main_problem="Needs website"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Website Development"
    )

    with database.get_connection() as db:

        row = db.execute(
            """
            SELECT
                event,
                actor_id,
                target_id
            FROM activity
            WHERE target_id = ?
            """,
            (
                opportunity_id,
            )
        ).fetchone()

    assert row is not None

    assert row["event"] == (
        "opportunity_created"
    )

    assert row["actor_id"] == business_id

    assert row["target_id"] == opportunity_id


def test_create_opportunity_requires_existing_business(
    test_database
):

    with pytest.raises(
        ValueError,
        match="Business not found"
    ):

        create_opportunity(
            business_id="B-does-not-exist",
            title="Invalid Opportunity"
        )


def test_list_opportunities(
    test_database
):

    business_id = create_business(
        name="List Business",
        owner="Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="Needs software"
    )

    create_opportunity(
        business_id=business_id,
        title="Software Development"
    )

    records = list_opportunities()

    assert len(records) == 1

    assert records[0]["business_id"] == (
        business_id
    )

    assert records[0]["business_name"] == (
        "List Business"
    )
