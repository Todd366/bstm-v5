import os


APP_NAME = os.getenv(
    "BSTM_APP_NAME",
    "BSTM Platform"
)

APP_VERSION = os.getenv(
    "BSTM_APP_VERSION",
    "5.0.0"
)

ENVIRONMENT = os.getenv(
    "BSTM_ENVIRONMENT",
    "development"
)

DATABASE_PATH = os.getenv(
    "BSTM_DATABASE",
    "bstm.db"
)

# Postgres (Supabase) connection string.
# Use the Supabase *session pooler* connection string (port 5432 on the
# pooler hostname, not the direct DB host) — the transaction pooler
# (port 6543) does not reliably preserve `SET search_path` across
# separate transactions on the same connection, which this app relies
# on (see app/db/database.py get_connection()). Verified against real
# production failures, not just documentation.
DATABASE_URL = os.getenv("BSTM_DATABASE_URL")

DB_SCHEMA = os.getenv("BSTM_DB_SCHEMA", "activation")

# Shared-secret API key required on every request except /, /health,
# the auto-generated docs routes, and youth self-registration/login
# (see AuthAndLoggingMiddleware and _PUBLIC_WRITES in app/main.py).
# This remains the right mechanism for admin/internal operations
# (business management, opportunity assignment, trial review) — real
# per-youth identity now goes through JWT_SECRET below instead.
# Deliberately has NO default: an unset key means auth is misconfigured,
# not "open".
API_KEY = os.getenv("BSTM_API_KEY")

# Signs/verifies youth login tokens (see app/services/auth_service.py).
# Deliberately no default, same reasoning as API_KEY — an unset secret
# should fail loudly, not silently issue tokens signed with a value
# anyone could guess.
JWT_SECRET = os.getenv("BSTM_JWT_SECRET")
