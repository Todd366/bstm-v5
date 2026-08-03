import os
import tempfile

import pytest

import app.core.config as config
import app.db.database as database

from app.services.business_service import (
    create_business
)

from app.services.capability_service import (
    assign_capability_to_youth,
    create_capability,
    list_youth_capabilities
)

from app.services.matching_service import (
    create_opportunity_match,
    list_youth_matches,
    match_youth_to_opportunities
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


def test_create_capability(
    test_database
):

    capability_id = create_capability(
        name="Web Development",
        category="Technology",
        description="Building websites and web applications."
    )

    assert capability_id.startswith(
        "CAP-"
    )


def test_assign_capability_to_youth(
    test_database
):

    youth_id = create_youth(
        name="Test Youth",
        location="Gaborone",
        passion="Technology",
        goal="Become a developer",
        skills="HTML, CSS"
    )

    capability_id = create_capability(
        name="Web Development",
        category="Technology"
    )

    youth_capability_id = (
        assign_capability_to_youth(
            youth_id=youth_id,
            capability_id=capability_id,
            level="Developing"
        )
    )

    assert youth_capability_id.startswith(
        "YC-"
    )

    records = list_youth_capabilities(
        youth_id
    )

    assert len(records) == 1

    assert records[0][
        "capability_name"
    ] == "Web Development"

    assert records[0][
        "level"
    ] == "Developing"


def test_match_youth_to_matching_opportunity(
    test_database
):

    youth_id = create_youth(
        name="Developer Youth",
        location="Gaborone",
        passion="Technology",
        goal="Build websites",
        skills="HTML, CSS, JavaScript"
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
        name="Digital Business",
        owner="Business Owner",
        sector="Retail",
        location="Gaborone",
        main_problem="Needs a website"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Web Development",
        description="Build a website for the business."
    )

    matches = match_youth_to_opportunities(
        youth_id
    )

    assert len(matches) == 1

    assert matches[0][
        "opportunity_id"
    ] == opportunity_id

    assert matches[0][
        "capability_name"
    ] == "Web Development"


def test_non_matching_youth_is_not_matched(
    test_database
):

    youth_id = create_youth(
        name="Marketing Youth",
        location="Gaborone",
        passion="Marketing",
        goal="Become a marketer",
        skills="Social media"
    )

    capability_id = create_capability(
        name="Digital Marketing",
        category="Marketing"
    )

    assign_capability_to_youth(
        youth_id=youth_id,
        capability_id=capability_id
    )

    business_id = create_business(
        name="Technology Business",
        owner="Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="Needs software"
    )

    create_opportunity(
        business_id=business_id,
        title="Web Development",
        description="Build a website."
    )

    matches = match_youth_to_opportunities(
        youth_id
    )

    assert len(matches) == 0


def test_create_opportunity_match(
    test_database
):

    youth_id = create_youth(
        name="Match Youth",
        location="Gaborone",
        passion="Technology",
        goal="Work on technology projects"
    )

    business_id = create_business(
        name="Match Business",
        owner="Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="Needs software"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Software Development"
    )

    match_id = create_opportunity_match(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_score=85,
        reason="Youth has relevant software development capability."
    )

    assert match_id.startswith(
        "MATCH-"
    )

    records = list_youth_matches(
        youth_id
    )

    assert len(records) == 1

    assert records[0][
        "match_id"
    ] == match_id

    assert records[0][
        "match_score"
    ] == 85

    assert records[0][
        "status"
    ] == "Pending"


def test_duplicate_match_is_not_created(
    test_database
):

    youth_id = create_youth(
        name="Duplicate Youth",
        location="Gaborone",
        passion="Technology",
        goal="Work"
    )

    business_id = create_business(
        name="Duplicate Business",
        owner="Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="Needs technology"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Technology Project"
    )

    first_match = create_opportunity_match(
        youth_id=youth_id,
        opportunity_id=opportunity_id
    )

    second_match = create_opportunity_match(
        youth_id=youth_id,
        opportunity_id=opportunity_id
    )

    assert first_match == second_match

    records = list_youth_matches(
        youth_id
    )

    assert len(records) == 1
