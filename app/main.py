"""
BSTM Activation OS — FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload

This replaces the old CLI-only main.py (kept as main_cli_legacy.py.bak).
All routes are thin wrappers around app.api.service — the actual business
logic lives in app.services.*, not here.
"""

import json
import logging
import secrets
import time
import traceback
import uuid

from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import API_KEY, APP_NAME, APP_VERSION, ENVIRONMENT

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
    list_youth_evidence_records,
    list_trial_evidence_records,
    submit_youth_evidence,
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


class _JSONLogFormatter(logging.Formatter):
    """Every log line comes out as one JSON object — Vercel captures
    stdout/stderr into its runtime logs regardless of format, but plain
    text isn't filterable or alertable. JSON is, including by anyone
    who later wires this up to a real log aggregator."""

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("request_id", "path", "method", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = "".join(
                traceback.format_exception(*record.exc_info)
            )
        return json.dumps(payload)


_handler = logging.StreamHandler()
_handler.setFormatter(_JSONLogFormatter())
logging.getLogger().handlers = [_handler]
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("bstm")


# CORS is left open for now (no confirmed frontend origin to lock it to
# yet) — but that's no longer the real access control. The API key
# middleware below is. CORS only restricts browser-originated requests
# anyway; it was never a substitute for real authentication.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths reachable with no API key: health checks and monitoring need to
# work without a secret, and the auto-generated docs are read-only.
_PUBLIC_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}

# (method, path) pairs that are public BY DESIGN, not oversight: these
# are the two self-service intake actions the real public-facing
# frontend (index.html / script.js "Door One" and "Door Two") needs to
# perform before the person filling them out has any credentials at
# all — youth self-registration and business self-registration.
# Embedding the admin X-API-Key in browser-shipped JS would leak it to
# anyone who views source, which would defeat the rest of this auth
# work the moment the frontend went live. Everything else (opportunity
# management, trial review, capability verification, and anything
# beyond the initial intake) stays behind the key.
#
# KNOWN GAP: neither endpoint has rate limiting yet. A stateless
# Vercel deployment can't do in-memory rate limiting reliably (no
# shared state between invocations) — a real fix needs an external
# store (e.g. Redis, or a Postgres-backed counter). Don't treat either
# as launch-ready for real public traffic until that's added.
_PUBLIC_WRITES = {("POST", "/youth"), ("POST", "/businesses")}


class AuthAndLoggingMiddleware:
    """Raw ASGI middleware, not the `@app.middleware("http")` /
    BaseHTTPMiddleware sugar — that pattern has a known limitation in
    the Starlette version bundled with our pinned fastapi<0.100: header
    mutations made on the response object *after* `call_next()` returns
    don't reliably reach the actual wire response (confirmed directly:
    X-Request-ID was silently absent from real responses). Operating at
    the raw ASGI level and intercepting the `http.response.start`
    message directly is correct regardless of that limitation.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        scope["state"] = {"request_id": request_id}

        method = scope["method"]
        path = scope["path"]
        headers = Headers(scope=scope)

        requires_auth = (
            method != "OPTIONS"
            and path not in _PUBLIC_PATHS
            and (method, path) not in _PUBLIC_WRITES
        )

        if requires_auth:
            if not API_KEY:
                # Deliberately fails closed: an unset key is a
                # misconfiguration, not "no auth needed".
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Server misconfigured: BSTM_API_KEY is not set."},
                )
                response.headers["X-Request-ID"] = request_id
                await response(scope, receive, send)
                return

            provided = headers.get("x-api-key", "")

            if not secrets.compare_digest(provided, API_KEY):
                response = JSONResponse(
                    status_code=401,
                    content={"detail": "Missing or invalid API key."},
                )
                response.headers["X-Request-ID"] = request_id
                await response(scope, receive, send)
                return

        start = time.monotonic()
        status_holder = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                message["headers"].append(
                    (b"x-request-id", request_id.encode("utf-8"))
                )
                status_holder["status_code"] = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "path": path,
                "method": method,
                "status_code": status_holder.get("status_code"),
                "duration_ms": duration_ms,
            },
        )


app.add_middleware(AuthAndLoggingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches anything _service_call's ValueError handling doesn't —
    real bugs, database errors (deadlocks, connection failures), etc.
    Without this, an uncaught exception just becomes Vercel's generic
    'FUNCTION_INVOCATION_FAILED' page: no structured log, and in some
    configurations the raw traceback leaks straight to the client.
    Logs the full traceback server-side, returns a clean, safe message
    with a request_id the person can report back for lookup."""

    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "unhandled exception",
        exc_info=exc,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error.",
            "request_id": request_id,
        },
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
    intake: Optional[dict] = None


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


class EvidenceSubmit(BaseModel):
    youth_id: str
    kind: str
    trial_id: Optional[str] = None
    capability_id: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


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


# ---------- evidence ----------

@app.post("/evidence", status_code=201)
def submit_evidence_route(payload: EvidenceSubmit):
    return _service_call(submit_youth_evidence, payload.dict())


@app.get("/youth/{youth_id}/evidence")
def list_youth_evidence_route(youth_id: str):
    return _service_call(list_youth_evidence_records, youth_id)


@app.get("/trials/{trial_id}/evidence")
def list_trial_evidence_route(trial_id: str):
    return _service_call(list_trial_evidence_records, trial_id)
