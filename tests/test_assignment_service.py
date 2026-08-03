import os
import tempfile

import pytest

import app.core.config as config
import app.db.database as database

from app.services.assignment_service import (
    accept_assignment,
    cancel_assignment,
    complete_assignment,
    create_assignment,
    decline_assignment,
    get_assignment,
    list_opportunity_assignments,
    list_youth_assignments
)

from app.services.business_service import (
    create_business
)

from app.services.capability_service import (
    assign_capability_to_youth,
    create_capability
)

from app.services.matching_service import (
    create_opportunity_match
)

from app.services.opportunity_service import (
    create_opportunity
)

from app.services.youth_service import (
    create_youth
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

    database.ensure_slice2_schema()

    database.ensure_slice3a_schema()

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


def create_test_entities():

    youth_id = create_youth(
        name="Assignment Youth",
        location="Gaborone",
        passion="Technology",
        goal="Work on technology projects",
        skills="Web Development"
    )

    capability_id = create_capability(
        name="Web Development",
        category="Technology"
    )

    assign_capability_to_youth(
        youth_id=youth_id,
        capability_id=capability_id,
        level="Intermediate"
    )

    business_id = create_business(
        name="Assignment Business",
        owner="Business Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="Needs a website"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Web Development",
        description="Build a website."
    )

    match_id = create_opportunity_match(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_score=90,
        reason="Relevant capability."
    )

    return (
        youth_id,
        opportunity_id,
        match_id
    )


def test_create_assignment(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    assert assignment_id.startswith(
        "ASSIGN-"
    )

    assignment = get_assignment(
        assignment_id
    )

    assert assignment[
        "youth_id"
    ] == youth_id

    assert assignment[
        "opportunity_id"
    ] == opportunity_id

    assert assignment[
        "match_id"
    ] == match_id

    assert assignment[
        "status"
    ] == "Pending"


def test_accept_assignment(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    accept_assignment(
        assignment_id
    )

    assignment = get_assignment(
        assignment_id
    )

    assert assignment[
        "status"
    ] == "Accepted"

    assert assignment[
        "accepted_at"
    ] is not None


def test_decline_assignment(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    decline_assignment(
        assignment_id
    )

    assignment = get_assignment(
        assignment_id
    )

    assert assignment[
        "status"
    ] == "Declined"


def test_cancel_assignment(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    cancel_assignment(
        assignment_id
    )

    assignment = get_assignment(
        assignment_id
    )

    assert assignment[
        "status"
    ] == "Cancelled"


def test_complete_assignment(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    accept_assignment(
        assignment_id
    )

    complete_assignment(
        assignment_id
    )

    assignment = get_assignment(
        assignment_id
    )

    assert assignment[
        "status"
    ] == "Completed"

    assert assignment[
        "completed_at"
    ] is not None


def test_completed_opportunity_counter_increments(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    accept_assignment(
        assignment_id
    )

    complete_assignment(
        assignment_id
    )

    with database.get_connection() as db:

        row = db.execute(
            """
            SELECT completed_opportunities
            FROM youth
            WHERE id = ?
            """,
            (
                youth_id,
            )
        ).fetchone()

    assert row[
        "completed_opportunities"
    ] == 1


def test_duplicate_assignment_is_rejected(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    with pytest.raises(
        ValueError,
        match="Assignment already exists"
    ):

        create_assignment(
            youth_id=youth_id,
            opportunity_id=opportunity_id,
            match_id=match_id
        )


def test_only_pending_assignment_can_be_accepted(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    accept_assignment(
        assignment_id
    )

    with pytest.raises(
        ValueError,
        match="Only pending assignments can be accepted"
    ):

        accept_assignment(
            assignment_id
        )


def test_only_accepted_assignment_can_be_completed(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    with pytest.raises(
        ValueError,
        match="Only accepted assignments can be completed"
    ):

        complete_assignment(
            assignment_id
        )


def test_list_youth_assignments(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    records = list_youth_assignments(
        youth_id
    )

    assert len(records) == 1

    assert records[0][
        "assignment_id"
    ] == assignment_id


def test_list_opportunity_assignments(
    test_database
):

    (
        youth_id,
        opportunity_id,
        match_id
    ) = create_test_entities()

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    records = list_opportunity_assignments(
        opportunity_id
    )

    assert len(records) == 1

    assert records[0][
        "assignment_id"
    ] == assignment_id

    assert records[0][
        "youth_id"
    ] == youth_id
