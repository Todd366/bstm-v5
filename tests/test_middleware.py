"""Access matrix for the ASGI middleware, exercised without FastAPI:
a dummy inner app answers 200 and echoes which identity the middleware set."""

import asyncio
import json

from app.core import middleware as mw
from app.services.auth_service import create_access_token

YOUTH = "11111111-1111-1111-1111-111111111111"
BIZ = "22222222-2222-2222-2222-222222222222"


async def _inner(scope, receive, send):
    st = scope.get("state", {})
    body = json.dumps({k: st.get(k) for k in ("youth_id", "business_id", "is_admin")}).encode()
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


def call(method, path, headers=None, rate_ok=True):
    hdrs = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {"type": "http", "method": method, "path": path, "headers": hdrs, "client": ("1.2.3.4", 1)}
    out = {}

    async def send(m):
        if m["type"] == "http.response.start":
            out["status"] = m["status"]
            out["headers"] = {k.decode(): v.decode() for k, v in m["headers"]}
        else:
            out["body"] = m.get("body", b"")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    original = mw.check_rate_limit
    mw.check_rate_limit = (lambda *a, **k: None) if rate_ok else original
    try:
        asyncio.run(mw.AuthAndLoggingMiddleware(_inner)(scope, receive, send))
    finally:
        mw.check_rate_limit = original
    return out["status"], out


def bearer(token):
    return {"Authorization": "Bearer " + token}


def test_youth_routes_need_youth_token_only():
    yt = create_access_token(YOUTH)
    bt = create_access_token(BIZ, role="business")
    assert call("GET", "/me")[0] == 401
    assert call("GET", "/me/earnings", bearer(bt))[0] == 401              # business token refused
    assert call("GET", "/me/earnings", {"X-API-Key": mw.API_KEY})[0] == 401  # admin key does not open /me
    status, out = call("GET", "/me/earnings", bearer(yt))
    assert status == 200 and json.loads(out["body"])["youth_id"] == YOUTH


def test_business_routes_need_business_token_only():
    yt = create_access_token(YOUTH)
    bt = create_access_token(BIZ, role="business")
    assert call("GET", "/biz")[0] == 401
    assert call("GET", "/biz/invoices", bearer(yt))[0] == 401             # youth token refused
    assert call("POST", "/biz/invoices/x/payments", {"X-API-Key": mw.API_KEY})[0] == 401
    status, out = call("GET", "/biz/invoices", bearer(bt))
    assert status == 200 and json.loads(out["body"])["business_id"] == BIZ


def test_admin_paths_need_the_key_and_tokens_do_not_substitute():
    yt = create_access_token(YOUTH)
    bt = create_access_token(BIZ, role="business")
    for path in ("/admin/queue", "/invoices", "/payments", "/payouts", "/youth", "/businesses", "/opportunities"):
        assert call("GET", path)[0] == 401, path
        assert call("GET", path, bearer(yt))[0] == 401, path
        assert call("GET", path, bearer(bt))[0] == 401, path
        assert call("GET", path, {"X-API-Key": "wrong"})[0] == 401, path
        assert call("GET", path, {"X-API-Key": mw.API_KEY})[0] == 200, path


def test_public_surface_is_exactly_what_is_listed():
    assert call("GET", "/health")[0] == 200
    assert call("GET", "/catalog/capabilities")[0] == 200
    assert call("GET", "/public/profiles/abc")[0] == 200
    assert call("POST", "/youth")[0] == 200
    assert call("POST", "/businesses")[0] == 200
    assert call("POST", "/businesses/login")[0] == 200
    assert call("POST", "/youth/login")[0] == 200
    assert call("POST", "/webhooks/sms-bridge")[0] == 200
    # near-misses stay closed
    assert call("POST", "/public/profiles/abc")[0] == 401
    assert call("GET", "/webhooks/sms-bridge")[0] == 401
    assert call("DELETE", "/youth")[0] == 401
    assert call("GET", "/publicx")[0] == 401


def test_admin_flag_is_set_on_public_paths_only_with_valid_key():
    _, out = call("GET", "/health", {"X-API-Key": mw.API_KEY})
    assert json.loads(out["body"])["is_admin"] is True
    _, out = call("GET", "/health", {"X-API-Key": "nope"})
    assert json.loads(out["body"])["is_admin"] is None


def test_security_headers_and_request_id_on_every_response():
    status, out = call("GET", "/health")
    h = out["headers"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert "default-src 'self'" in h["content-security-policy"] and "x-request-id" in h
    assert "content-security-policy" not in call("GET", "/docs")[1]["headers"]
    assert "x-request-id" in call("GET", "/admin/queue")[1]["headers"]       # even on 401


def test_oversized_body_is_refused():
    status, _ = call("POST", "/youth", {"Content-Length": str(mw.MAX_BODY_BYTES + 1)})
    assert status == 413


def test_throttled_ip_gets_429():
    from app.core.errors import RateLimitExceeded
    original = mw.check_rate_limit
    def deny(*a, **k):
        raise RateLimitExceeded("Too many requests")
    mw.check_rate_limit = deny
    try:
        scope_status = None
        hdrs = []
        out = {}
        async def send(m):
            if m["type"] == "http.response.start":
                out["status"] = m["status"]
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        scope = {"type": "http", "method": "POST", "path": "/businesses/login", "headers": hdrs, "client": ("9.9.9.9", 1)}
        asyncio.run(mw.AuthAndLoggingMiddleware(_inner)(scope, receive, send))
        assert out["status"] == 429
    finally:
        mw.check_rate_limit = original


def test_public_staff_signup_route_is_open_and_rate_limited_path():
    assert call("POST", "/staff/signup")[0] == 200
    assert call("GET", "/staff/signup")[0] == 401
