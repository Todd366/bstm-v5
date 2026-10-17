"""
BSTM Activation OS — FastAPI application entrypoint.

Run locally:   uvicorn app.main:app --reload
Vercel entry:  pyproject.toml [tool.vercel] entrypoint = "app.main:app"

Layout
  app/routes/     HTTP only (public_routes, me_routes, admin_routes)
  app/api/        use-case functions called by routes
  app/services/   business rules + SQL
  app/core/       config, errors, validation, middleware, logging
  public/         the frontend (index.html, app.js, app.css)
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.core.logging_setup import configure_logging
from app.core.middleware import AuthAndLoggingMiddleware
from app.routes.admin_routes import router as admin_router
from app.routes.biz_routes import router as biz_router
from app.routes.me_routes import router as me_router
from app.routes.public_routes import router as public_router

configure_logging()
logger = logging.getLogger("bstm")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Human Capital + Opportunity + Business Activation OS",
)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

# Added last so it is the outermost layer: it sees every request first.
app.add_middleware(AuthAndLoggingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Anything the routes did not translate: log the full traceback
    server-side, return a safe message plus a request id the person can
    quote."""

    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "unhandled exception: %s: %s", type(exc).__name__, str(exc)[:200],
        exc_info=exc,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again.", "request_id": request_id},
    )


app.include_router(public_router)
app.include_router(me_router)
app.include_router(biz_router)
app.include_router(admin_router)
