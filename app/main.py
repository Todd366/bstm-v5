"""
BSTM Activation OS — FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload

This replaces the old CLI-only main.py (kept as main_cli_legacy.py.bak).
All routes are thin wrappers around app.api.service — the actual business
logic lives in app.services.*, not here.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import APP_NAME, APP_VERSION, ENVIRONMENT

from app.api.service import (
    accept_opportunity_assignment,
    activate_business,
    activate_youth,
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
    list_youth,
    list_youth_capability_records,
    list_youth_opportunity_assignments,
    list_youth_opportunity_matches,
    list_youth_opportunity_trials,
    match_youth_opportunity,
    review_opportunity_trial,
    start_opportunity_trial,
    submit_opportunity_trial,
    update_business_audit_status,
    verify_youth_capability,
)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Human Capital + Opportunity + Business Activation OS",
)

# NOTE: wide open for now so the frontend and any client can reach the API
# during early development. Lock this down to the real frontend origin(s)
# before this goes properly live.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _service_call(fn, *args, **kwargs):
    """Runs a service-layer call and translates ValueError into the right
    HTTP status: 404 if the message says something wasn't found, 400 for
    every other validation failure (already-exists, invalid state, etc)."""

    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message)


# ---------- schemas ----------

class YouthCreate(BaseModel):
    name: str
    location: str
    goal: str
    passion: Optional[str] = None
    availability: Optional[str] = None
    equipment: Optional[str] = None


class BusinessCreate(BaseModel):
    name: str
    owner: str
    sector: str
    location: str
    main_problem: str


class AuditStatusUpdate(BaseModel):
    status: str


class OpportunityCreate(BaseModel):
    business_id: str
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    budget: float = 0


class CapabilityCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None


class CapabilityAssign(BaseModel):
    capability_id: str
    level: str = "Beginner"


class CapabilityVerify(BaseModel):
    verified: bool = True


class MatchCreate(BaseModel):
    youth_id: str
    opportunity_id: str
    match_score: float = 0
    reason: Optional[dict] = None


class AssignmentCreate(BaseModel):
    youth_id: str
    opportunity_id: str
    match_id: Optional[str] = None


class TrialCreate(BaseModel):
    assignment_id: str
    title: Optional[str] = None
    description: Optional[str] = None


class TrialSubmission(BaseModel):
    submission: Optional[dict] = None


class TrialReview(BaseModel):
    review: Optional[dict] = None


class TrialCancel(BaseModel):
    reason: Optional[str] = None


# ---------- platform ----------

@app.get("/health")
def health():
    return _service_call(get_dashboard)


@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "docs": "/docs",
    }


# ---------- youth ----------

@app.post("/youth", status_code=201)
def create_youth_route(payload: YouthCreate):
    return _service_call(activate_youth, payload.dict())


@app.get("/youth")
def list_youth_route():
    return _service_call(list_youth)


@app.get("/youth/{youth_id}")
def get_youth_route(youth_id: str):
    return _service_call(get_youth_profile, youth_id)


@app.get("/youth/{youth_id}/capabilities")
def list_youth_capabilities_route(youth_id: str):
    return _service_call(list_youth_capability_records, youth_id)


@app.post("/youth/{youth_id}/capabilities", status_code=201)
def assign_youth_capability_route(youth_id: str, payload: CapabilityAssign):
    body = payload.dict()
    body["youth_id"] = youth_id
    return _service_call(assign_youth_capability, body)


@app.get("/youth/{youth_id}/opportunities/discover")
def discover_opportunities_route(youth_id: str):
    return _service_call(find_youth_opportunities, youth_id)


@app.get("/youth/{youth_id}/matches")
def list_youth_matches_route(youth_id: str):
    return _service_call(list_youth_opportunity_matches, youth_id)


@app.get("/youth/{youth_id}/assignments")
def list_youth_assignments_route(youth_id: str):
    return _service_call(list_youth_opportunity_assignments, youth_id)


@app.get("/youth/{youth_id}/trials")
def list_youth_trials_route(youth_id: str):
    return _service_call(list_youth_opportunity_trials, youth_id)


# ---------- capabilities ----------

@app.post("/capabilities", status_code=201)
def create_capability_route(payload: CapabilityCreate):
    return _service_call(create_youth_capability, payload.dict())


@app.get("/capabilities")
def list_capabilities_route():
    return _service_call(list_capability_records)


@app.post("/youth-capabilities/{youth_capability_id}/verify")
def verify_capability_route(youth_capability_id: str, payload: CapabilityVerify):
    return _service_call(verify_youth_capability, youth_capability_id, payload.verified)


# ---------- businesses ----------

@app.post("/businesses", status_code=201)
def create_business_route(payload: BusinessCreate):
    return _service_call(activate_business, payload.dict())


@app.get("/businesses")
def list_businesses_route():
    return _service_call(list_businesses)


@app.get("/businesses/{business_id}")
def get_business_route(business_id: str):
    return _service_call(get_business_profile, business_id)


@app.post("/businesses/{business_id}/audit-status")
def update_audit_status_route(business_id: str, payload: AuditStatusUpdate):
    return _service_call(update_business_audit_status, business_id, payload.status)


# ---------- opportunities ----------

@app.post("/opportunities", status_code=201)
def create_opportunity_route(payload: OpportunityCreate):
    return _service_call(create_business_opportunity, payload.dict())


@app.get("/opportunities")
def list_opportunities_route():
    return _service_call(list_business_opportunities)


@app.get("/opportunities/{opportunity_id}")
def get_opportunity_route(opportunity_id: str):
    return _service_call(get_business_opportunity, opportunity_id)


@app.get("/opportunities/{opportunity_id}/assignments")
def list_opportunity_assignments_route(opportunity_id: str):
    return _service_call(list_opportunity_assignment_records, opportunity_id)


# ---------- matches ----------

@app.post("/matches", status_code=201)
def create_match_route(payload: MatchCreate):
    return _service_call(match_youth_opportunity, payload.dict())


# ---------- assignments ----------

@app.post("/assignments", status_code=201)
def create_assignment_route(payload: AssignmentCreate):
    return _service_call(assign_opportunity, payload.dict())


@app.get("/assignments/{assignment_id}")
def get_assignment_route(assignment_id: str):
    return _service_call(get_opportunity_assignment, assignment_id)


@app.post("/assignments/{assignment_id}/accept")
def accept_assignment_route(assignment_id: str):
    return _service_call(accept_opportunity_assignment, assignment_id)


@app.post("/assignments/{assignment_id}/decline")
def decline_assignment_route(assignment_id: str):
    return _service_call(decline_opportunity_assignment, assignment_id)


@app.post("/assignments/{assignment_id}/cancel")
def cancel_assignment_route(assignment_id: str):
    return _service_call(cancel_opportunity_assignment, assignment_id)


@app.post("/assignments/{assignment_id}/complete")
def complete_assignment_route(assignment_id: str):
    return _service_call(complete_opportunity_assignment, assignment_id)


@app.get("/assignments/{assignment_id}/trials")
def list_assignment_trials_route(assignment_id: str):
    return _service_call(list_assignment_opportunity_trials, assignment_id)


# ---------- trials ----------

@app.post("/trials", status_code=201)
def create_trial_route(payload: TrialCreate):
    return _service_call(create_assignment_trial, payload.dict())


@app.get("/trials/{trial_id}")
def get_trial_route(trial_id: str):
    return _service_call(get_opportunity_trial, trial_id)


@app.post("/trials/{trial_id}/start")
def start_trial_route(trial_id: str):
    return _service_call(start_opportunity_trial, trial_id)


@app.post("/trials/{trial_id}/submit")
def submit_trial_route(trial_id: str, payload: TrialSubmission):
    return _service_call(submit_opportunity_trial, trial_id, payload.submission)


@app.post("/trials/{trial_id}/review")
def review_trial_route(trial_id: str, payload: TrialReview):
    return _service_call(review_opportunity_trial, trial_id, payload.review)


@app.post("/trials/{trial_id}/complete")
def complete_trial_route(trial_id: str, payload: TrialReview):
    return _service_call(complete_opportunity_trial, trial_id, payload.review)


@app.post("/trials/{trial_id}/cancel")
def cancel_trial_route(trial_id: str, payload: TrialCancel):
    return _service_call(cancel_opportunity_trial, trial_id, payload.reason)
