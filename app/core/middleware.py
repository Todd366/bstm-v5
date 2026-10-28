"""
Raw ASGI middleware: request id, auth tiers, rate limiting, body-size
limit, security headers, request logging.

Raw ASGI rather than @app.middleware("http"): header changes made after
call_next() do not reliably reach the wire on the Starlette bundled with
our pinned FastAPI, so we intercept `http.response.start` directly.

Auth tiers
  public     static files, /health, docs, catalog, and a few self-service
             writes (register, login, business register) — rate limited.
  youth JWT  everything under /me.
  staff      everything else: a staff Bearer token (role-limited, see
             app.core.permissions) or the break-glass X-API-Key (admin).
"""

import asyncio
import logging
import secrets
import time
import uuid

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from app.core.config import (
    API_KEY,
    MAX_BODY_BYTES,
    RATE_LOGIN_PER_HOUR_IP,
    RATE_REGISTER_PER_HOUR,
)
from app.core.errors import RateLimitExceeded
from app.core.permissions import allowed_roles
from app.services.auth_service import decode_access_token, decode_token_payload
from app.services.staff_service import lookup_active_staff
from app.services.rate_limit_service import check_rate_limit

logger = logging.getLogger("bstm")

PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/app.js",
    "/app.css",
    "/favicon.svg",
    "/manifest.webmanifest",
    "/sw.js",
    "/catalog/capabilities",
    "/catalog/departments",
}

# Self-service actions that must work before the person has any
# credentials. Each is rate limited per client IP.
PUBLIC_WRITES = {
    ("POST", "/youth"): ("register", RATE_REGISTER_PER_HOUR),
    ("POST", "/businesses"): ("register-business", RATE_REGISTER_PER_HOUR),
    ("POST", "/youth/login"): ("login", RATE_LOGIN_PER_HOUR_IP),
    ("POST", "/businesses/login"): ("login-business", RATE_LOGIN_PER_HOUR_IP),
    ("POST", "/staff/login"): ("login-staff", RATE_LOGIN_PER_HOUR_IP),
    ("POST", "/auth/reset"): ("reset", RATE_LOGIN_PER_HOUR_IP),
}

# Public by prefix. Webhooks authenticate by HMAC signature inside the
# route; public profiles only ever return data the owner opted to share.
PUBLIC_GET_PREFIXES = ("/public/profiles/",)
PUBLIC_POST_PREFIXES = ("/webhooks/",)
WEBHOOK_RATE_PER_HOUR = 600

# Documentation pages load scripts from a CDN, so the strict CSP below
# is not applied to them.
_NO_CSP_PATHS = {"/docs", "/redoc"}

_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"cross-origin-opener-policy", b"same-origin"),
]


def is_youth_path(path):
    return path == "/me" or path.startswith("/me/")


def is_business_path(path):
    return path == "/biz" or path.startswith("/biz/")


def _bearer(headers):
    auth_header = headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def client_ip(scope, headers):
    """Vercel puts the real client address first in X-Forwarded-For;
    scope["client"] behind a proxy is the proxy itself."""

    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    client = scope.get("client")
    return client[0] if client else None


def _json(status, detail, request_id, **extra):
    response = JSONResponse(status_code=status, content={"detail": detail, **extra})
    response.headers["X-Request-ID"] = request_id
    return response


class AuthAndLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        method = scope["method"]
        path = scope["path"]
        headers = Headers(scope=scope)

        early = await self._guard(scope, headers, method, path, state, request_id)

        if early is not None:
            await early(scope, receive, send)
            return

        start = time.monotonic()
        status_holder = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_headers = message.setdefault("headers", [])
                response_headers.append((b"x-request-id", request_id.encode("utf-8")))
                response_headers.extend(_SECURITY_HEADERS)
                if path not in _NO_CSP_PATHS:
                    response_headers.append((b"content-security-policy", _CSP.encode("utf-8")))
                status_holder["status_code"] = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "path": path,
                "method": method,
                "status_code": status_holder.get("status_code"),
                "duration_ms": round((time.monotonic() - start) * 1000, 2),
            },
        )

    async def _guard(self, scope, headers, method, path, state, request_id):
        """Returns a response to send instead of running the app, or
        None to let the request through."""

        # Body-size ceiling (Content-Length). Vercel enforces its own
        # hard limit too; this keeps junk out of the JSON parser.
        length = headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return _json(413, "Request body too large.", request_id)

        if method == "OPTIONS":
            return None

        for matches, role, state_key in (
            (is_youth_path, "youth", "youth_id"),
            (is_business_path, "business", "business_id"),
        ):
            if matches(path):
                token = _bearer(headers)

                try:
                    subject = decode_access_token(token, role=role) if token else None
                except RuntimeError:
                    return _json(500, "Server misconfigured: BSTM_JWT_SECRET is not set.", request_id)

                if not subject:
                    return _json(401, "Missing or invalid access token.", request_id)

                state[state_key] = subject
                return None

        rule = PUBLIC_WRITES.get((method, path))

        if rule is None and method == "POST" and path.startswith(PUBLIC_POST_PREFIXES):
            rule = ("webhook", WEBHOOK_RATE_PER_HOUR)

        is_public_get = method == "GET" and path.startswith(PUBLIC_GET_PREFIXES)

        if rule is None and path not in PUBLIC_PATHS and not is_public_get:
            return await self._staff_guard(headers, method, path, state, request_id)

        if rule is not None:
            endpoint, limit = rule
            ip = client_ip(scope, headers)

            try:
                # Blocking DB call: run in a thread so the event loop
                # stays free.
                await asyncio.to_thread(check_rate_limit, ip, endpoint, limit, 60)
            except RateLimitExceeded as exc:
                return _json(429, str(exc), request_id)
            except Exception:
                # Rate limiting is protection, not a dependency: if the
                # database is unreachable the request itself will fail
                # with a clear error, so don't turn this into a second,
                # confusing failure.
                logger.warning("rate limit check failed", exc_info=True,
                               extra={"request_id": request_id, "path": path, "method": method})

        # Admin recognised on public paths too (lets /health show detail).
        provided = headers.get("x-api-key", "")
        if API_KEY and provided and secrets.compare_digest(
            provided.encode("utf-8"), API_KEY.encode("utf-8")
        ):
            state["is_admin"] = True

        return None


    async def _staff_guard(self, headers, method, path, state, request_id):
        """Staff tier: break-glass API key (admin) or an individual staff
        token limited to its role. A deactivated account stops working at
        once because the account is re-checked on every request."""

        provided = headers.get("x-api-key", "")

        if provided:
            if API_KEY and secrets.compare_digest(provided.encode("utf-8"), API_KEY.encode("utf-8")):
                state.update(is_admin=True, actor="admin-key", staff_role="admin", staff_id=None)
                return None
            return _json(401, "Missing or invalid credentials.", request_id)

        token = _bearer(headers)

        if token:
            try:
                payload = decode_token_payload(token, "staff")
            except RuntimeError:
                return _json(500, "Server misconfigured: BSTM_JWT_SECRET is not set.", request_id)

            if payload:
                try:
                    staff = await asyncio.to_thread(lookup_active_staff, payload["sub"])
                except Exception:
                    logger.warning("staff lookup failed", exc_info=True, extra={"request_id": request_id})
                    return _json(503, "Service temporarily unavailable.", request_id)

                if staff:
                    if staff["role"] not in allowed_roles(method, path):
                        return _json(403, "Your role is not allowed to do this.", request_id)

                    state.update(is_admin=staff["role"] == "admin", actor=staff["name"],
                                 staff_role=staff["role"], staff_id=payload["sub"])
                    return None

        if not API_KEY and not token:
            return _json(500, "Server misconfigured: BSTM_API_KEY is not set.", request_id)

        return _json(401, "Missing or invalid credentials.", request_id)
