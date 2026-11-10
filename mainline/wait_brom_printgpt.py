#!/usr/bin/env python3
"""Z301ML: await MediaTek BROM handshake, bypass DAA and print GPT. READ-ONLY.
Prepare BEFORE user physically disconnects USB and reconnects holding ONLY Vol-.
No eMMC write commands and no DA FINISH or reset.
"""
import os,sys,runpy
os.chdir("/Users/matveysazhnov/mtkclient")
sys.path.insert(0,os.getcwd())
sys.modules["mfusepy"]=None
sys.argv=["mtk.py","printgpt"]
print("WAITING FOR Z301ML BROM PRELOADER HANDSHAKE — Vol- ONLY; NO FLASH",flush=True)
runpy.run_path("mtk.py",run_name="__main__")
