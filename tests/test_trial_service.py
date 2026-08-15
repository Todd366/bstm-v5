from tests.helpers import _is_valid_uuid

import pytest

from app.services.assignment_service import (
    accept_assignment,
    create_assignment
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

from app.services.trial_service import (
    cancel_trial,
    complete_trial,
    create_trial,
    get_trial,
    list_assignment_trials,
    list_youth_trials,
    review_trial,
    start_trial,
    submit_trial
)

from app.services.youth_service import (
    create_youth
)


def create_test_assignment():

    youth_id = create_youth(
        name="Trial Youth",
        location="Gaborone",
        passion="Technology",
        goal="Complete technology trials",
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
        name="Trial Business",
        owner="Trial Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="Needs a website"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Website Development Trial",
        description="Build and test a business website."
    )

    match_id = create_opportunity_match(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_score=95,
        reason="Strong capability match."
    )

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id
    )

    accept_assignment(
        assignment_id
    )

    return (
        youth_id,
        opportunity_id,
        assignment_id
    )


def test_create_trial(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id=assignment_id
    )

    assert _is_valid_uuid(
        trial_id
    )

    trial = get_trial(
        trial_id
    )

    assert trial[
        "assignment_id"
    ] == assignment_id

    assert trial[
        "youth_id"
    ] == youth_id

    assert trial[
        "opportunity_id"
    ] == opportunity_id

    assert trial[
        "status"
    ] == "Created"


def test_only_accepted_assignment_can_create_trial(
    test_database
):

    youth_id = create_youth(
        name="Unaccepted Youth",
        location="Gaborone",
        passion="Technology",
        goal="Learn",
    )

    business_id = create_business(
        name="Unaccepted Business",
        owner="Owner",
        sector="Technology",
        location="Gaborone",
        main_problem="Needs software"
    )

    opportunity_id = create_opportunity(
        business_id=business_id,
        title="Software Trial",
        description="Build software."
    )

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id
    )

    with pytest.raises(
        ValueError,
        match="Only accepted assignments can create trials"
    ):

        create_trial(
            assignment_id
        )


def test_duplicate_trial_is_rejected(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    create_trial(
        assignment_id
    )

    with pytest.raises(
        ValueError,
        match="Trial already exists"
    ):

        create_trial(
            assignment_id
        )


def test_start_trial(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    start_trial(
        trial_id
    )

    trial = get_trial(
        trial_id
    )

    assert trial[
        "status"
    ] == "Active"

    assert trial[
        "started_at"
    ] is not None


def test_submit_trial(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    start_trial(
        trial_id
    )

    submit_trial(
        trial_id,
        "Website submitted for testing."
    )

    trial = get_trial(
        trial_id
    )

    assert trial[
        "status"
    ] == "Submitted"

    assert trial[
        "submission"
    ] == "Website submitted for testing."

    assert trial[
        "submitted_at"
    ] is not None


def test_review_trial(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    start_trial(
        trial_id
    )

    submit_trial(
        trial_id,
        "Completed work."
    )

    review_trial(
        trial_id,
        "Reviewing submitted work."
    )

    trial = get_trial(
        trial_id
    )

    assert trial[
        "status"
    ] == "Under Review"

    assert trial[
        "review"
    ] == "Reviewing submitted work."

    assert trial[
        "reviewed_at"
    ] is not None


def test_complete_trial(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    start_trial(
        trial_id
    )

    submit_trial(
        trial_id,
        "Final submission."
    )

    review_trial(
        trial_id,
        "Approved."
    )

    complete_trial(
        trial_id
    )

    trial = get_trial(
        trial_id
    )

    assert trial[
        "status"
    ] == "Completed"

    assert trial[
        "completed_at"
    ] is not None


def test_completed_trial_counter_increments(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    start_trial(
        trial_id
    )

    submit_trial(
        trial_id
    )

    review_trial(
        trial_id
    )

    complete_trial(
        trial_id
    )

    with database.get_connection() as db:

        row = db.execute(
            """
            SELECT completed_trials
            FROM youth
            WHERE id = ?
            """,
            (
                youth_id,
            )
        ).fetchone()

    assert row[
        "completed_trials"
    ] == 1


def test_cancel_trial(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    cancel_trial(
        trial_id,
        "Business cancelled the project."
    )

    trial = get_trial(
        trial_id
    )

    assert trial[
        "status"
    ] == "Cancelled"

    assert trial[
        "cancellation_reason"
    ] == "Business cancelled the project."

    assert trial[
        "cancelled_at"
    ] is not None


def test_completed_trial_cannot_be_cancelled(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    start_trial(
        trial_id
    )

    submit_trial(
        trial_id
    )

    review_trial(
        trial_id
    )

    complete_trial(
        trial_id
    )

    with pytest.raises(
        ValueError,
        match="Completed or cancelled trials cannot be cancelled"
    ):

        cancel_trial(
            trial_id
        )


def test_invalid_trial_transition_is_rejected(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    with pytest.raises(
        ValueError,
        match="Only active trials can be submitted"
    ):

        submit_trial(
            trial_id
        )


def test_list_youth_trials(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    records = list_youth_trials(
        youth_id
    )

    assert len(records) == 1

    assert records[0][
        "trial_id"
    ] == trial_id


def test_list_assignment_trials(
    test_database
):

    (
        youth_id,
        opportunity_id,
        assignment_id
    ) = create_test_assignment()

    trial_id = create_trial(
        assignment_id
    )

    records = list_assignment_trials(
        assignment_id
    )

    assert len(records) == 1

    assert records[0][
        "trial_id"
    ] == trial_id

    assert records[0][
        "youth_id"
    ] == youth_id
