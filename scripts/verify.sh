#!/usr/bin/env sh
# Run the full test-suite against YOUR database in a throw-away schema
# (created and dropped automatically; real data is never touched).
# Usage: BSTM_DATABASE_URL='postgresql://...' sh scripts/verify.sh
set -e
[ -n "$BSTM_DATABASE_URL" ] || { echo "Set BSTM_DATABASE_URL first"; exit 1; }
python -m pip install -q -r requirements-dev.txt
python -c "import app.main" && echo "import OK"
python -m pytest -q
