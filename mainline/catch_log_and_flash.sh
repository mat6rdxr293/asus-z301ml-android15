#!/bin/zsh
# wait BROM -> DA; read expdb to crashlogs/expdb-$TAG.bin; flash IMAGE + BCB + finish
IMG=$1; TAG=$2
cd /Users/matveysazhnov/mtkclient
sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u -c 'import sys,runpy; sys.modules["mfusepy"]=None; sys.argv=["mtk.py","printgpt"]; runpy.run_path("mtk.py",run_name="__main__")' > /Users/matveysazhnov/ASUS-Z301ML-port/mainline/crashlogs/catch-$TAG.log 2>&1
cd /Users/matveysazhnov/ASUS-Z301ML-port/mainline
echo "DA UP $(date +%T)"
sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u da_read_expdb.py crashlogs/expdb-$TAG.bin 2>&1 | grep -E "EXPDB|Error|Traceback"
sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u flash_recovery_and_bcb.py "$IMG" $3 2>&1 | tr '\r' '\n' | grep -vE 'Progress|^\s*$|Done'
