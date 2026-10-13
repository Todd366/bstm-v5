"""Shared helpers for route modules."""

import psycopg2
from fastapi import HTTPException

from app.core.errors import Conflict, Forbidden, RateLimitExceeded


def service_call(fn, *args, **kwargs):
    """Runs a service/use-case call and maps its errors to HTTP:

      RateLimitExceeded → 429, Forbidden → 403, Conflict → 409,
      other ValueError  → 404 if the message says "not found", else 400,
      a malformed value that reached Postgres → 400.
    """

    try:
        return fn(*args, **kwargs)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Forbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message)
    except (psycopg2.errors.InvalidTextRepresentation, psycopg2.errors.DataError):
        raise HTTPException(status_code=400, detail="Invalid value in request.")


def youth_id_of(request):
    """The authenticated youth's id. Set by the auth middleware from a
    verified JWT — never taken from the URL or body."""

    return request.state.youth_id
