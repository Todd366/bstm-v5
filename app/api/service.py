"""
Use-case layer between HTTP routes and services.

Each function takes plain data, returns plain data, and raises
ValueError (or a subclass from app.core.errors) for anything the caller
did wrong. Routes translate those into HTTP statuses.
"""

from app.core.departments import DEPARTMENTS
from app.core.health import system_health
from app.core.validation import clean_text, require_uuid

from app.services.assignment_service import (
    accept_assignment,
    cancel_assignment,
    complete_assignment,
    create_assignment,
    decline_assignment,
    get_assignment,
    list_opportunity_assignments,
    list_youth_assignments,
)
from app.services.auth_service import create_access_token
from app.services.business_service import (
    create_business,
    get_business,
    list_businesses as list_business_records,
    set_audit_status,
)
from app.services.capability_service import (
    assign_capability_to_youth,
    create_capability,
    list_capabilities,
    list_youth_capabilities,
    verify_capability,
)
from app.services.evidence_service import (
    list_trial_evidence,
    list_youth_evidence,
    submit_evidence,
)
from app.services.matching_service import (
    create_opportunity_match,
    list_youth_matches,
    match_youth_to_opportunities,
)
from app.services.opportunity_service import (
    browse_open_opportunities,
    create_opportunity,
    get_opportunity,
    list_opportunities,
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
    submit_trial,
)
from app.services.youth_service import (
    authenticate_youth,
    create_youth,
    get_youth,
    list_youth as list_youth_records,
)


# ---------- public ----------

def activate_youth(data):
    """Registers a youth and signs them in at once (no second trip to a
    login screen)."""

    youth_id = create_youth(
        name=data["name"],
        location=data["location"],
        passion=data.get("passion"),
        goal=data["goal"],
        email=data["email"],
        password=data["password"],
        availability=data.get("availability"),
        equipment=data.get("equipment"),
        intake=data.get("intake"),
        capabilities=data.get("capabilities"),
    )

    return {
        "status": "created",
        "id": youth_id,
        "access_token": create_access_token(youth_id),
        "token_type": "bearer",
    }


def login_youth(data):

    youth_id = authenticate_youth(email=data["email"], password=data["password"])

    return {
        "status": "authenticated",
        "access_token": create_access_token(youth_id),
        "token_type": "bearer",
    }


def activate_business(data):

    business_id = create_business(
        name=data["name"],
        owner=data["owner"],
        sector=data["sector"],
        location=data["location"],
        main_problem=data["main_problem"],
    )

    return {"status": "created", "id": business_id}


def get_capability_catalog(category=None):
    return list_capabilities(category)


def get_department_list():
    return list(DEPARTMENTS)


# ---------- youth self-service (youth_id always comes from the JWT) ----------

def get_my_profile(youth_id):
    return get_youth(youth_id)


def get_my_capabilities(youth_id):
    return list_youth_capabilities(youth_id)


def claim_my_capability(youth_id, data):
    """Self-claimed capabilities are always unverified."""

    youth_capability_id = assign_capability_to_youth(
        youth_id=youth_id,
        capability_id=data["capability_id"],
        level=data.get("level", "Beginner"),
    )

    return {"status": "claimed", "id": youth_capability_id}


def get_my_matches(youth_id):
    return match_youth_to_opportunities(youth_id)


def browse_my_opportunities(youth_id):
    return browse_open_opportunities(youth_id)


def apply_to_opportunity(youth_id, opportunity_id):
    """Applies. The opportunity stays open for others until BSTM
    accepts an applicant."""

    opportunity_id = require_uuid(opportunity_id, "Opportunity")

    match_id = create_opportunity_match(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_score=50,
        reason={"source": "self_application"},
    )

    assignment_id = create_assignment(
        youth_id=youth_id,
        opportunity_id=opportunity_id,
        match_id=match_id,
        mode="application",
    )

    return {"status": "applied", "match_id": match_id, "assignment_id": assignment_id}


def get_my_assignments(youth_id):
    return list_youth_assignments(youth_id)


def accept_my_assignment(youth_id, assignment_id):
    return {
        "status": "accepted",
        "id": accept_assignment(assignment_id, acting_youth_id=youth_id),
    }


def decline_my_assignment(youth_id, assignment_id):
    return {
        "status": "declined",
        "id": decline_assignment(assignment_id, acting_youth_id=youth_id),
    }


def withdraw_my_assignment(youth_id, assignment_id):
    return {
        "status": "cancelled",
        "id": cancel_assignment(assignment_id, acting_youth_id=youth_id),
    }


def get_my_trials(youth_id):
    return list_youth_trials(youth_id)


def create_my_trial(youth_id, assignment_id):
    """Starts the proof-of-work for an accepted assignment: creates the
    trial and marks it active in one step."""

    trial_id = create_trial(assignment_id, acting_youth_id=youth_id)
    start_trial(trial_id, acting_youth_id=youth_id)

    return {"status": "active", "id": trial_id}


def get_my_trial(youth_id, trial_id):
    return get_trial(trial_id, acting_youth_id=youth_id)


def submit_my_trial(youth_id, trial_id, submission):
    return {
        "status": "submitted",
        "id": submit_trial(trial_id, submission, acting_youth_id=youth_id),
    }


def cancel_my_trial(youth_id, trial_id, reason):
    return {
        "status": "cancelled",
        "id": cancel_trial(trial_id, reason, acting_youth_id=youth_id),
    }


def get_my_evidence(youth_id):
    return list_youth_evidence(youth_id)


def submit_my_evidence(youth_id, data):
    evidence_id = submit_evidence(
        youth_id=youth_id,
        kind=data["kind"],
        trial_id=data.get("trial_id"),
        capability_id=data.get("capability_id"),
        url=data.get("url"),
        notes=data.get("notes"),
    )

    return {"status": "submitted", "id": evidence_id}


# ---------- admin ----------

def get_dashboard():
    health = system_health()

    return {
        "platform": {
            "name": health["service"],
            "version": health["version"],
            "environment": health["environment"],
            "status": health["status"],
        },
        "database": health["database"],
        "counts": health["counts"],
    }


def list_youth(limit=50, offset=0):
    return list_youth_records(limit, offset)


def get_youth_profile(youth_id):
    return get_youth(youth_id)


def list_businesses(limit=50, offset=0):
    return list_business_records(limit, offset)


def get_business_profile(business_id):
    return get_business(business_id)


def update_business_audit_status(business_id, status):
    return set_audit_status(business_id, status)


def create_business_opportunity(data):

    opportunity_id = create_opportunity(
        business_id=data["business_id"],
        title=data["title"],
        description=data.get("description"),
        department=data.get("department"),
        budget=data.get("budget", 0),
    )

    return {"status": "created", "id": opportunity_id}


def list_business_opportunities(limit=100, offset=0, status=None):
    return list_opportunities(limit, offset, status)


def get_business_opportunity(opportunity_id):
    return get_opportunity(opportunity_id)


def create_youth_capability(data):

    capability_id = create_capability(
        name=data["name"],
        category=data["category"],
        description=data.get("description"),
    )

    return {"status": "created", "id": capability_id}


def assign_youth_capability(data):

    youth_capability_id = assign_capability_to_youth(
        youth_id=data["youth_id"],
        capability_id=data["capability_id"],
        level=data.get("level", "Beginner"),
    )

    return {"status": "assigned", "id": youth_capability_id}


def list_capability_records():
    return list_capabilities()


def list_youth_capability_records(youth_id):
    return list_youth_capabilities(youth_id)


def verify_youth_capability(youth_capability_id, verified=True):
    return verify_capability(youth_capability_id, verified)


def find_youth_opportunities(youth_id):
    return match_youth_to_opportunities(youth_id)


def match_youth_opportunity(data):

    match_id = create_opportunity_match(
        youth_id=data["youth_id"],
        opportunity_id=data["opportunity_id"],
        match_score=data.get("match_score", 0),
        reason=data.get("reason"),
    )

    return {"status": "matched", "id": match_id}


def list_youth_opportunity_matches(youth_id):
    return list_youth_matches(youth_id)


def assign_opportunity(data):

    assignment_id = create_assignment(
        youth_id=data["youth_id"],
        opportunity_id=data["opportunity_id"],
        match_id=data.get("match_id"),
        mode="offer",
    )

    return {"status": "assigned", "id": assignment_id}


def accept_opportunity_assignment(assignment_id):
    return {"status": "accepted", "id": accept_assignment(assignment_id)}


def decline_opportunity_assignment(assignment_id):
    return {"status": "declined", "id": decline_assignment(assignment_id)}


def cancel_opportunity_assignment(assignment_id):
    return {"status": "cancelled", "id": cancel_assignment(assignment_id)}


def complete_opportunity_assignment(assignment_id):
    return {"status": "completed", "id": complete_assignment(assignment_id)}


def get_opportunity_assignment(assignment_id):
    return get_assignment(assignment_id)


def list_youth_opportunity_assignments(youth_id):
    return list_youth_assignments(youth_id)


def list_opportunity_assignment_records(opportunity_id):
    return list_opportunity_assignments(opportunity_id)


def create_assignment_trial(data):

    trial_id = create_trial(
        assignment_id=data["assignment_id"],
        title=data.get("title"),
        description=data.get("description"),
    )

    return {"status": "created", "id": trial_id}


def start_opportunity_trial(trial_id):
    return {"status": "active", "id": start_trial(trial_id)}


def submit_opportunity_trial(trial_id, submission=None):
    return {"status": "submitted", "id": submit_trial(trial_id, submission)}


def review_opportunity_trial(trial_id, review=None):
    return {"status": "under_review", "id": review_trial(trial_id, review)}


def complete_opportunity_trial(trial_id, review=None):
    return {"status": "completed", "id": complete_trial(trial_id, review)}


def cancel_opportunity_trial(trial_id, reason=None):
    return {"status": "cancelled", "id": cancel_trial(trial_id, reason)}


def get_opportunity_trial(trial_id):
    return get_trial(trial_id)


def list_youth_opportunity_trials(youth_id):
    return list_youth_trials(youth_id)


def list_assignment_opportunity_trials(assignment_id):
    return list_assignment_trials(assignment_id)


def submit_youth_evidence(data):

    evidence_id = submit_evidence(
        youth_id=data["youth_id"],
        kind=data["kind"],
        trial_id=data.get("trial_id"),
        capability_id=data.get("capability_id"),
        url=data.get("url"),
        notes=data.get("notes"),
    )

    return {"status": "submitted", "id": evidence_id}


def list_youth_evidence_records(youth_id):
    return list_youth_evidence(youth_id)


def list_trial_evidence_records(trial_id):
    return list_trial_evidence(trial_id)
