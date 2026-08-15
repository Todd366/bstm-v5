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
# On Vercel (serverless), use the Supabase *pooler* connection string
# (port 6543, pgbouncer transaction mode) — not the direct DB connection —
# because serverless functions open/close connections per-request and
# the direct connection limit will exhaust fast.
DATABASE_URL = os.getenv("BSTM_DATABASE_URL")

DB_SCHEMA = os.getenv("BSTM_DB_SCHEMA", "activation")
