from tests.helpers import _is_valid_uuid

import pytest

from app.db.database import transaction

from app.services.business_service import (
    create_business
)

from app.services.opportunity_service import (
    create_opportunity,
    get_opportunity,
    list_opportunities
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

    assert _is_valid_uuid(
        opportunity_id
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

    with transaction() as db:

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

    assert row["opportunities_generated"] == 1


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

    with transaction() as db:

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
            business_id="00000000-0000-0000-0000-000000000000",
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
