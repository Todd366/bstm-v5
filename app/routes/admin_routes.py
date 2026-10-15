"""Admin routes: guarded by the X-API-Key header (middleware)."""

from fastapi import APIRouter, Query

from app.api.service import (
    close_business_opportunity,
    get_activity,
    get_opportunity_candidates,
    get_business_diagnosis,
    get_field_audits,
    get_review_queue,
    record_field_audit,
    accept_opportunity_assignment,
    assign_opportunity,
    assign_youth_capability,
    cancel_opportunity_assignment,
    cancel_opportunity_trial,
    complete_opportunity_assignment,
    complete_opportunity_trial,
    create_assignment_trial,
    create_business_opportunity,
    create_youth_capability,
    decline_opportunity_assignment,
    find_youth_opportunities,
    get_business_opportunity,
    get_business_profile,
    get_dashboard,
    get_opportunity_assignment,
    get_opportunity_trial,
    get_youth_profile,
    list_assignment_opportunity_trials,
    list_business_opportunities,
    list_businesses,
    list_capability_records,
    list_opportunity_assignment_records,
    list_trial_evidence_records,
    list_youth,
    list_youth_capability_records,
    list_youth_evidence_records,
    list_youth_opportunity_assignments,
    list_youth_opportunity_matches,
    list_youth_opportunity_trials,
    match_youth_opportunity,
    review_opportunity_trial,
    start_opportunity_trial,
    submit_opportunity_trial,
    submit_youth_evidence,
    update_business_audit_status,
    verify_youth_capability,
)
from app.routes.common import service_call
from app.schemas.models import (
    FieldAuditCreate,
    AssignmentCreate,
    AuditStatusUpdate,
    CapabilityAssign,
    CapabilityCreate,
    CapabilityVerify,
    EvidenceSubmit,
    MatchCreate,
    OpportunityCreate,
    TrialCancel,
    TrialCreate,
    TrialReview,
    TrialSubmission,
)

router = APIRouter(tags=["admin"])


@router.get("/admin/stats")
def stats():
    return service_call(get_dashboard)


@router.get("/admin/queue")
def queue():
    return service_call(get_review_queue)


@router.get("/admin/activity")
def activity(limit: int = Query(50, ge=1, le=200)):
    return service_call(get_activity, limit)


@router.get("/opportunities/{opportunity_id}/candidates")
def opportunity_candidates(opportunity_id: str):
    return service_call(get_opportunity_candidates, opportunity_id)


@router.post("/opportunities/{opportunity_id}/close")
def opportunity_close(opportunity_id: str):
    return service_call(close_business_opportunity, opportunity_id)


@router.post("/audits", status_code=201)
def audit_create(payload: FieldAuditCreate):
    return service_call(record_field_audit, payload.dict())


@router.get("/audits")
def audit_list(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return service_call(get_field_audits, limit, offset)


@router.get("/businesses/{business_id}/diagnosis")
def business_diagnosis(business_id: str):
    return service_call(get_business_diagnosis, business_id)


# ----- youth -----

@router.get("/youth")
def youth_list(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return service_call(list_youth, limit, offset)


@router.get("/youth/{youth_id}")
def youth_get(youth_id: str):
    return service_call(get_youth_profile, youth_id)


@router.get("/youth/{youth_id}/capabilities")
def youth_capabilities(youth_id: str):
    return service_call(list_youth_capability_records, youth_id)


@router.post("/youth/{youth_id}/capabilities", status_code=201)
def youth_capability_assign(youth_id: str, payload: CapabilityAssign):
    body = payload.dict()
    body["youth_id"] = youth_id
    return service_call(assign_youth_capability, body)


@router.get("/youth/{youth_id}/opportunities/discover")
def youth_discover(youth_id: str):
    return service_call(find_youth_opportunities, youth_id)


@router.get("/youth/{youth_id}/matches")
def youth_matches(youth_id: str):
    return service_call(list_youth_opportunity_matches, youth_id)


@router.get("/youth/{youth_id}/assignments")
def youth_assignments(youth_id: str):
    return service_call(list_youth_opportunity_assignments, youth_id)


@router.get("/youth/{youth_id}/trials")
def youth_trials(youth_id: str):
    return service_call(list_youth_opportunity_trials, youth_id)


@router.get("/youth/{youth_id}/evidence")
def youth_evidence(youth_id: str):
    return service_call(list_youth_evidence_records, youth_id)


# ----- capabilities -----

@router.post("/capabilities", status_code=201)
def capability_create(payload: CapabilityCreate):
    return service_call(create_youth_capability, payload.dict())


@router.get("/capabilities")
def capability_list():
    return service_call(list_capability_records)


@router.post("/youth-capabilities/{youth_capability_id}/verify")
def capability_verify(youth_capability_id: str, payload: CapabilityVerify):
    return service_call(verify_youth_capability, youth_capability_id, payload.verified)


# ----- businesses -----

@router.get("/businesses")
def business_list(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return service_call(list_businesses, limit, offset)


@router.get("/businesses/{business_id}")
def business_get(business_id: str):
    return service_call(get_business_profile, business_id)


@router.post("/businesses/{business_id}/audit-status")
def business_audit_status(business_id: str, payload: AuditStatusUpdate):
    return service_call(update_business_audit_status, business_id, payload.status)


# ----- opportunities -----

@router.post("/opportunities", status_code=201)
def opportunity_create(payload: OpportunityCreate):
    return service_call(create_business_opportunity, payload.dict())


@router.get("/opportunities")
def opportunity_list(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query(None, max_length=20),
):
    return service_call(list_business_opportunities, limit, offset, status)


@router.get("/opportunities/{opportunity_id}")
def opportunity_get(opportunity_id: str):
    return service_call(get_business_opportunity, opportunity_id)


@router.get("/opportunities/{opportunity_id}/assignments")
def opportunity_assignments(opportunity_id: str):
    return service_call(list_opportunity_assignment_records, opportunity_id)


# ----- matches / assignments -----

@router.post("/matches", status_code=201)
def match_create(payload: MatchCreate):
    return service_call(match_youth_opportunity, payload.dict())


@router.post("/assignments", status_code=201)
def assignment_create(payload: AssignmentCreate):
    return service_call(assign_opportunity, payload.dict())


@router.get("/assignments/{assignment_id}")
def assignment_get(assignment_id: str):
    return service_call(get_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/accept")
def assignment_accept(assignment_id: str):
    return service_call(accept_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/decline")
def assignment_decline(assignment_id: str):
    return service_call(decline_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/cancel")
def assignment_cancel(assignment_id: str):
    return service_call(cancel_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/complete")
def assignment_complete(assignment_id: str):
    return service_call(complete_opportunity_assignment, assignment_id)


@router.get("/assignments/{assignment_id}/trials")
def assignment_trials(assignment_id: str):
    return service_call(list_assignment_opportunity_trials, assignment_id)


# ----- trials -----

@router.post("/trials", status_code=201)
def trial_create(payload: TrialCreate):
    return service_call(create_assignment_trial, payload.dict())


@router.get("/trials/{trial_id}")
def trial_get(trial_id: str):
    return service_call(get_opportunity_trial, trial_id)


@router.post("/trials/{trial_id}/start")
def trial_start(trial_id: str):
    return service_call(start_opportunity_trial, trial_id)


@router.post("/trials/{trial_id}/submit")
def trial_submit(trial_id: str, payload: TrialSubmission):
    return service_call(submit_opportunity_trial, trial_id, payload.submission)


@router.post("/trials/{trial_id}/review")
def trial_review(trial_id: str, payload: TrialReview):
    return service_call(review_opportunity_trial, trial_id, payload.review)


@router.post("/trials/{trial_id}/complete")
def trial_complete(trial_id: str, payload: TrialReview):
    return service_call(complete_opportunity_trial, trial_id, payload.review)


@router.post("/trials/{trial_id}/cancel")
def trial_cancel(trial_id: str, payload: TrialCancel):
    return service_call(cancel_opportunity_trial, trial_id, payload.reason)


@router.get("/trials/{trial_id}/evidence")
def trial_evidence(trial_id: str):
    return service_call(list_trial_evidence_records, trial_id)


# ----- evidence -----

@router.post("/evidence", status_code=201)
def evidence_submit(payload: EvidenceSubmit):
    return service_call(submit_youth_evidence, payload.dict())
