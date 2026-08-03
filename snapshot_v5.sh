#!/data/data/com.termux/files/usr/bin/bash
cd ~/bstm-activation/bstm_v5

echo "============================================================"
echo "BSTM V5 FULL SNAPSHOT"
echo "============================================================"

echo -e "\n### DIRECTORY TREE ###"
find app tests -type f -name "*.py" | sort

echo -e "\n### FILE CONTENTS ###"
for f in $(find app tests -type f -name "*.py" | sort); do
    echo -e "\n===== $f ====="
    cat "$f"
done

echo -e "\n### SCHEMA ###"
python - <<'PY'
import sqlite3
db = sqlite3.connect("bstm.db")
for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    print(f"\n--- {name} ---")
    for row in db.execute(f"PRAGMA table_info({name})"):
        print(row)
db.close()
PY

echo -e "\n### TEST RUN ###"
python -m pytest -q

echo -e "\n============================================================"
echo "SNAPSHOT COMPLETE"
echo "============================================================"
