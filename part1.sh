#!/data/data/com.termux/files/usr/bin/bash
cd ~/bstm-activation/bstm_v5
echo "### PART 1: api + core ###"
for f in app/api/cli.py app/api/service.py app/core/config.py app/core/health.py app/core/ids.py app/core/time.py; do
    echo -e "\n===== $f ====="
    cat "$f"
done
