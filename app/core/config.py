import os


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


APP_NAME = os.getenv("BSTM_APP_NAME", "BSTM Platform")

APP_VERSION = os.getenv("BSTM_APP_VERSION", "5.14.0")

ENVIRONMENT = os.getenv("BSTM_ENVIRONMENT", "development")

# Postgres (Supabase) connection string.
# Use the Supabase *session pooler* connection string (port 5432 on the
# pooler hostname, not the direct DB host) — the transaction pooler
# (port 6543) does not reliably preserve `SET search_path` across
# separate transactions on the same connection, which this app relies
# on (see app/db/database.py get_connection()).
DATABASE_URL = os.getenv("BSTM_DATABASE_URL")

DB_SCHEMA = os.getenv("BSTM_DB_SCHEMA", "activation")

# Shared-secret admin key. Deliberately NO default: an unset key means
# auth is misconfigured, not "open".
OWNER_EMAIL = (os.getenv("BSTM_OWNER_EMAIL") or "bstm366@gmail.com").strip().lower()
OWNER_ID = "00000000-0000-4000-8000-000000000001"   # the built-in owner has no database row
OWNER_PASSWORD = os.getenv("BSTM_OWNER_PASSWORD")
API_KEY = os.getenv("BSTM_STAFF_KEY") or os.getenv("BSTM_API_KEY")

# Signs/verifies youth login tokens. Deliberately no default.
JWT_SECRET = os.getenv("BSTM_JWT_SECRET")

# Comma-separated list of origins allowed to call the API from a
# browser. The bundled frontend is served from the same origin, so in
# production the default is "no cross-origin access". Development
# defaults to "*" so a local file/other port can reach it.
_cors = os.getenv("BSTM_CORS_ORIGINS")
if _cors is None:
    CORS_ORIGINS = ["*"] if ENVIRONMENT != "production" else []
else:
    CORS_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]

# Request body ceiling (bytes). Registration payloads are a few KB.
MAX_BODY_BYTES = _int("BSTM_MAX_BODY_BYTES", 64 * 1024)

# Rate limits (requests per window, per key). Registration is per IP and
# deliberately generous: many people in Botswana share one mobile-carrier
# (CGNAT) address, and a school or youth hub shares one connection.
RATE_REGISTER_PER_HOUR = _int("BSTM_RATE_REGISTER_PER_HOUR", 30)
RATE_LOGIN_PER_HOUR_IP = _int("BSTM_RATE_LOGIN_PER_HOUR_IP", 60)
RATE_LOGIN_PER_15MIN_ACCOUNT = _int("BSTM_RATE_LOGIN_PER_15MIN_ACCOUNT", 8)

# Maximum simultaneously open applications one youth may hold.
MAX_OPEN_APPLICATIONS = _int("BSTM_MAX_OPEN_APPLICATIONS", 5)

# Shown to businesses on their invoices: where to send the money (e.g.
# "MyZaka 7xxxxxxx - BSTM Activation. Use the invoice number as reference.").
PAY_INSTRUCTIONS = os.getenv(
    "BSTM_PAY_INSTRUCTIONS",
    "Ask your BSTM contact for the payment details, then submit the payment reference here.",
)
