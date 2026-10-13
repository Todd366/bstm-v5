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
    login_youth,
)
from app.core.health import liveness
from app.routes.common import service_call
from app.schemas.models import BusinessCreate, YouthCreate, YouthLogin

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
