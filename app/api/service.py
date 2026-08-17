import json

from app.core.health import system_health
from app.db.database import transaction

from app.services.capability_service import (
    assign_capability_to_youth,
    create_capability,
    list_capabilities,
    list_youth_capabilities,
    verify_capability
)

from app.services.matching_service import (
    create_opportunity_match,
    list_youth_matches,
    match_youth_to_opportunities
)

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

from app.services.business_service import (
    create_business,
    get_business,
    list_businesses as list_business_records,
    set_audit_status
)

from app.services.opportunity_service import (
    create_opportunity,
    get_opportunity,
    list_opportunities
)

from app.services.youth_service import (
    create_youth,
    get_youth
)

from app.services.evidence_service import (
    list_trial_evidence,
    list_youth_evidence,
    submit_evidence
)


def activate_youth(data):

    youth_id = create_youth(
        name=data["name"],
        location=data["location"],
        passion=data.get("passion"),
        goal=data["goal"],
        availability=data.get("availability"),
        equipment=data.get("equipment"),
        intake=data.get("intake")
    )

    return {
        "status": "created",
        "id": youth_id
    }


def activate_business(data):

    business_id = create_business(
        name=data["name"],
        owner=data["owner"],
        sector=data["sector"],
        location=data["location"],
        main_problem=data["main_problem"]
    )

    return {
        "status": "created",
        "id": business_id
    }


def create_business_opportunity(
    data
):

    opportunity_id = create_opportunity(
        business_id=data["business_id"],
        title=data["title"],
        description=data.get(
            "description"
        )
    )

    return {
        "status": "created",
        "id": opportunity_id
    }



def create_youth_capability(data):

    capability_id = create_capability(
        name=data["name"],
        category=data["category"],
        description=data.get("description")
    )

    return {
        "status": "created",
        "id": capability_id
    }


def assign_youth_capability(data):

    youth_capability_id = assign_capability_to_youth(
        youth_id=data["youth_id"],
        capability_id=data["capability_id"],
        level=data.get("level", "Beginner")
    )

    return {
        "status": "assigned",
        "id": youth_capability_id
    }


def list_capability_records():

    return list_capabilities()


def list_youth_capability_records(youth_id):

    return list_youth_capabilities(
        youth_id
    )


def find_youth_opportunities(youth_id):

    return match_youth_to_opportunities(
        youth_id
    )


def match_youth_opportunity(data):

    match_id = create_opportunity_match(
        youth_id=data["youth_id"],
        opportunity_id=data["opportunity_id"],
        match_score=data.get("match_score", 0),
        reason=data.get("reason")
    )

    return {
        "status": "matched",
        "id": match_id
    }


def list_youth_opportunity_matches(youth_id):

    return list_youth_matches(
        youth_id
    )



def assign_opportunity(data):

    assignment_id = create_assignment(
        youth_id=data["youth_id"],
        opportunity_id=data["opportunity_id"],
        match_id=data.get("match_id")
    )

    return {
        "status": "assigned",
        "id": assignment_id
    }


def accept_opportunity_assignment(
    assignment_id
):

    assignment_id = accept_assignment(
        assignment_id
    )

    return {
        "status": "accepted",
        "id": assignment_id
    }


def decline_opportunity_assignment(
    assignment_id
):

    assignment_id = decline_assignment(
        assignment_id
    )

    return {
        "status": "declined",
        "id": assignment_id
    }


def cancel_opportunity_assignment(
    assignment_id
):

    assignment_id = cancel_assignment(
        assignment_id
    )

    return {
        "status": "cancelled",
        "id": assignment_id
    }


def complete_opportunity_assignment(
    assignment_id
):

    assignment_id = complete_assignment(
        assignment_id
    )

    return {
        "status": "completed",
        "id": assignment_id
    }


def get_opportunity_assignment(
    assignment_id
):

    return get_assignment(
        assignment_id
    )


def list_youth_opportunity_assignments(
    youth_id
):

    return list_youth_assignments(
        youth_id
    )


def list_opportunity_assignment_records(
    opportunity_id
):

    return list_opportunity_assignments(
        opportunity_id
    )



def create_assignment_trial(data):

    trial_id = create_trial(
        assignment_id=data["assignment_id"],
        title=data.get("title"),
        description=data.get("description")
    )

    return {
        "status": "created",
        "id": trial_id
    }


def start_opportunity_trial(
    trial_id
):

    trial_id = start_trial(
        trial_id
    )

    return {
        "status": "active",
        "id": trial_id
    }


def submit_opportunity_trial(
    trial_id,
    submission=None
):

    trial_id = submit_trial(
        trial_id,
        submission
    )

    return {
        "status": "submitted",
        "id": trial_id
    }


def review_opportunity_trial(
    trial_id,
    review=None
):

    trial_id = review_trial(
        trial_id,
        review
    )

    return {
        "status": "under_review",
        "id": trial_id
    }


def complete_opportunity_trial(
    trial_id,
    review=None
):

    trial_id = complete_trial(
        trial_id,
        review
    )

    return {
        "status": "completed",
        "id": trial_id
    }


def cancel_opportunity_trial(
    trial_id,
    reason=None
):

    trial_id = cancel_trial(
        trial_id,
        reason
    )

    return {
        "status": "cancelled",
        "id": trial_id
    }


def get_opportunity_trial(
    trial_id
):

    return get_trial(
        trial_id
    )


def list_youth_opportunity_trials(
    youth_id
):

    return list_youth_trials(
        youth_id
    )


def list_assignment_opportunity_trials(
    assignment_id
):

    return list_assignment_trials(
        assignment_id
    )


def list_youth():

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                id,
                name,
                location,
                passion,
                goal,
                availability,
                equipment,
                level,
                capability_score,
                learning_score,
                reputation_score,
                reliability_score,
                completed_trials,
                completed_opportunities,
                revenue,
                created_at
            FROM youth
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def list_businesses():

    with transaction() as db:

        rows = db.execute(
            """
            SELECT
                id,
                name,
                owner,
                sector,
                location,
                main_problem,
                audit_status,
                opportunities_generated,
                created_at
            FROM businesses
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def list_business_opportunities():

    return list_opportunities()


def get_business_opportunity(
    opportunity_id
):

    return get_opportunity(
        opportunity_id
    )


def get_dashboard():

    health = system_health()

    return {
        "platform": {
            "name": health["service"],
            "version": health["version"],
            "environment": health["environment"],
            "status": health["status"]
        },
        "database": health["database"],
        "counts": health["counts"]
    }


def get_youth_profile(youth_id):

    return get_youth(youth_id)


def verify_youth_capability(youth_capability_id, verified=True):

    return verify_capability(youth_capability_id, verified)


def get_business_profile(business_id):

    return get_business(business_id)


def update_business_audit_status(business_id, status):

    return set_audit_status(business_id, status)


def submit_youth_evidence(data):

    evidence_id = submit_evidence(
        youth_id=data["youth_id"],
        kind=data["kind"],
        trial_id=data.get("trial_id"),
        capability_id=data.get("capability_id"),
        url=data.get("url"),
        notes=data.get("notes")
    )

    return {
        "status": "submitted",
        "id": evidence_id
    }


def list_youth_evidence_records(youth_id):

    return list_youth_evidence(
        youth_id
    )


def list_trial_evidence_records(trial_id):

    return list_trial_evidence(
        trial_id
    )
