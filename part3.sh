#!/data/data/com.termux/files/usr/bin/bash
cd ~/bstm-activation/bstm_v5
echo "### PART 3: matching + assignment + trial ###"
for f in app/services/matching_service.py app/services/assignment_service.py app/services/trial_service.py; do
    echo -e "\n===== $f ====="
    cat "$f"
done
