#!/bin/zsh
# wait for BROM (hold Vol- while plugging), bring up DA, then flash IMAGE to recovery + BCB + finish
IMG=$1
cd /Users/matveysazhnov/mtkclient
sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u -c 'import sys,runpy; sys.modules["mfusepy"]=None; sys.argv=["mtk.py","printgpt"]; runpy.run_path("mtk.py",run_name="__main__")' > /Users/matveysazhnov/ASUS-Z301ML-port/mainline/crashlogs/catch-$(date +%H%M%S).log 2>&1
cd /Users/matveysazhnov/ASUS-Z301ML-port/mainline
echo "DA UP $(date +%T)"
sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u flash_recovery_and_bcb.py "$IMG" $3 2>&1 | tr '\r' '\n' | grep -vE 'Progress|^\s*$|Done'
