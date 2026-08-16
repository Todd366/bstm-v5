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
# and the auto-generated docs routes. There is no per-user login system
# yet — this is a stopgap appropriate for the system's current maturity,
# not a long-term replacement for real auth once BSTM has user accounts.
# Deliberately has NO default: an unset key means auth is misconfigured,
# not "open" — see require_api_key() in app/main.py.
API_KEY = os.getenv("BSTM_API_KEY")
