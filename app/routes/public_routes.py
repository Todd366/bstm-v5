"""Routes anyone can call: health, frontend files, catalog, and the
self-service register/login actions (rate limited in the middleware)."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.api.service import (
    activate_business,
    activate_youth,
    get_capability_catalog,
    get_department_list,
    ingest_provider_event,
    login_business,
    login_staff,
    redeem_reset,
    staff_signup,
    login_youth,
    view_public_profile,
)
from app.core.health import liveness
from app.routes.common import service_call
from app.schemas.models import BusinessCreate, BusinessLogin, ResetRedeem, StaffLogin, StaffSignup, YouthCreate, YouthLogin

router = APIRouter()

PUBLIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "public",
)

_NO_CACHE = {"Cache-Control": "no-cache"}
_ASSET_CACHE = {"Cache-Control": "public, max-age=300"}


@router.get("/health")
def health(request: Request):
    """Liveness + database reachability. Reveals only status; an admin
    key adds the underlying error text to help diagnose outages."""

    ok, payload, message = liveness()

    if not ok and message and getattr(request.state, "is_admin", False):
        payload["error"] = message

    return JSONResponse(status_code=200 if ok else 503, content=payload)


def _static(name, media_type, headers):
    return FileResponse(os.path.join(PUBLIC_DIR, name), media_type=media_type, headers=headers)


@router.get("/")
def index():
    return _static("index.html", "text/html", _NO_CACHE)


@router.get("/app.js")
def app_js():
    return _static("app.js", "application/javascript", _ASSET_CACHE)


@router.get("/app.css")
def app_css():
    return _static("app.css", "text/css", _ASSET_CACHE)


@router.get("/sw.js")
def service_worker():
    return _static("sw.js", "application/javascript", _NO_CACHE)


@router.get("/favicon.svg")
def favicon():
    return _static("favicon.svg", "image/svg+xml", _ASSET_CACHE)


@router.get("/manifest.webmanifest")
def manifest():
    return _static("manifest.webmanifest", "application/manifest+json", _ASSET_CACHE)


@router.get("/catalog/capabilities")
def catalog_capabilities():
    return service_call(get_capability_catalog)


@router.get("/catalog/departments")
def catalog_departments():
    return get_department_list()


@router.post("/youth", status_code=201)
def register_youth(payload: YouthCreate):
    return service_call(activate_youth, payload.dict())


@router.post("/youth/login")
def login(payload: YouthLogin):
    return service_call(login_youth, payload.dict())


@router.post("/businesses", status_code=201)
def register_business(payload: BusinessCreate):
    return service_call(activate_business, payload.dict())


@router.post("/businesses/login")
def login_biz(payload: BusinessLogin):
    return service_call(login_business, payload.dict())


@router.post("/staff/login")
def login_staff_route(payload: StaffLogin):
    return service_call(login_staff, payload.dict())


@router.post("/staff/signup", status_code=201)
def signup_staff_route(payload: StaffSignup):
    return service_call(staff_signup, payload.dict())


@router.post("/auth/reset")
def reset_password(payload: ResetRedeem):
    return service_call(redeem_reset, payload.dict())


@router.get("/public/profiles/{youth_id}")
def public_profile(youth_id: str):
    return service_call(view_public_profile, youth_id)


@router.post("/webhooks/{provider}")
async def provider_webhook(provider: str, request: Request):
    """Signed events from a payment provider or automation. Authenticity
    is the HMAC signature, not the admin key. Idempotent."""

    body = await request.body()
    return service_call(ingest_provider_event, provider, request.headers, body)
