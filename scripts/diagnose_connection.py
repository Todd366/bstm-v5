"""
Standalone diagnostic — no pytest, no fixtures, no app code beyond the
raw DB connection. Runs 20 trivial queries back to back and times each
one individually. If the network is silently dropping the connection
mid-session, this will show exactly which attempt stalls and for how
long, without any other moving parts to muddy the signal.

Run: python3 diagnose_connection.py
"""

import os
import time

import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("BSTM_DATABASE_URL")

if not DATABASE_URL:
    raise SystemExit("Set BSTM_DATABASE_URL first")

print(f"Connecting...")
t0 = time.monotonic()
conn = psycopg2.connect(
    DATABASE_URL,
    cursor_factory=psycopg2.extras.RealDictCursor,
    connect_timeout=10,
    keepalives=1,
    keepalives_idle=5,
    keepalives_interval=2,
    keepalives_count=2,
)
print(f"Connected in {time.monotonic() - t0:.2f}s")

with conn.cursor() as cur:
    cur.execute("SET statement_timeout = 8000")
conn.commit()

for i in range(1, 21):
    t0 = time.monotonic()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT %s AS n", (i,))
            row = cur.fetchone()
        elapsed = time.monotonic() - t0
        print(f"query {i:2d}: OK  ({elapsed:.2f}s)  result={row['n']}")
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"query {i:2d}: FAILED after {elapsed:.2f}s -> {type(e).__name__}: {e}")
        break
    time.sleep(1)

conn.close()
print("Done.")
