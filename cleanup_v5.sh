#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/bstm-activation/bstm_v5

echo "Backing up before cleanup..."
cp bstm.db "bstm_pre_cleanup_$(date +%Y%m%d_%H%M%S).db" 2>/dev/null || true
mkdir -p .cleanup_backup
cp -r app/core/database.py app/models .cleanup_backup/ 2>/dev/null || true
cp app/services/trial_service.py.before_utc_repair .cleanup_backup/ 2>/dev/null || true
cp app/services/trial_service.py.broken_import_backup .cleanup_backup/ 2>/dev/null || true

echo "Removing dead SQLAlchemy layer (unused, broken import chain)..."
rm -f app/core/database.py
rm -rf app/models

echo "Removing stale backup files..."
rm -f app/services/trial_service.py.before_utc_repair
rm -f app/services/trial_service.py.broken_import_backup

echo "Running test suite to confirm nothing broke..."
python -m pytest -q

echo ""
echo "Cleanup complete. Removed files backed up in .cleanup_backup/"
