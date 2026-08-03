#!/data/data/com.termux/files/usr/bin/bash
cd ~/bstm-activation/bstm_v5
echo "### PART 2: services ###"
for f in app/services/business_service.py app/services/opportunity_service.py app/services/capability_service.py; do
    echo -e "\n===== $f ====="
    cat "$f"
done
