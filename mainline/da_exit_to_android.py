#!/usr/bin/env python3
"""ASUS Z301ML: leave legacy DA into HOME_SCREEN mode (not mode 0 power off).
No eMMC writes. Recovery flash image must be readback-verified before proceeding.
"""
import os,sys,hashlib,json,subprocess,logging
from pathlib import Path
H=Path("/Users/matveysazhnov")
MTK=H/"mtkclient"
STATE=MTK/".state"
W=H/"ASUS-Z301ML-port/mainline/recovery-readcheck"
ACTUAL=W/"recovery-live-after-flash.bin"
EXPECTED=H/"ASUS-Z301ML-port/output/z301ml-test-recovery-318-FULL16MiB-UNSIGNED-DO_NOT_FLASH.img"
SHA="e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2"
def check(ok,msg):
    if not ok: raise RuntimeError("STOP: "+msg)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in (ACTUAL,EXPECTED):
    check(p.is_file() and p.stat().st_size==16777216 and digest(p)==SHA,"flash readback mismatches experimental image: "+str(p))
check(STATE.exists(),"Existing DA state missing")
s=json.loads(STATE.read_text())
check(s.get("hwcode")==0x321 and s.get("meid")=="e38fd44f882d91c96dfa77e29b2cc032" and s.get("flashmode")=="LEGACY","Wrong device DA")
out=subprocess.run(["ioreg","-p","IOUSB","-l","-w0"],capture_output=True,text=True,timeout=7,check=True).stdout
check('"idVendor" = 3725' in out and '"idProduct" = 8193' in out,"Device is not in DA USB 0e8d:2001 mode")
print("PASS: exact recovery readback SHA256 and existing matching USB DA confirmed",flush=True)
if "--check" in sys.argv:
    print("DRY-RUN OK: no commands sent to USB",flush=True)
    sys.exit(0)
check(os.geteuid()==0,"sudo/root needed for USB")
os.chdir(MTK)
sys.path.insert(0,str(MTK))
sys.modules["mfusepy"]=None
from mtkclient.config.mtk_config import MtkConfig
from mtkclient.Library.mtk_class import Mtk
from mtkclient.Library.DA.mtk_da_handler import DaHandler
from mtkclient.Library.Partitions.gpt import GptSettings
config=MtkConfig(loglevel=logging.INFO)
config.gpt_settings=GptSettings(0,0,0)
mtk=Mtk(config=config,loglevel=logging.INFO)
da=DaHandler(mtk,logging.INFO)
print("Reconnecting to already-running legacy DA, no BROM handshake",flush=True)
mtk=da.connect(mtk,directory=".")
check(mtk is not None and mtk.reinited,"DA session not resumed")
mtk=da.configure_da(mtk)
check(mtk is not None and mtk.config.hwcode==0x321,"Incorrect legacy DA")
print("Issuing corrected legacy DA FINISH in HOME_SCREEN mode (1). No eMMC writes.",flush=True)
ack = mtk.daloader.da.finish(1)
print("DA FINISH HOME_SCREEN ACK accepted:",ack,flush=True)
if not ack:
    print("STOP: DA did not confirm finish; keeping transport connected for diagnosis",flush=True)
    sys.exit(3)
print("DA acknowledged bootmode 1; requesting USB transport reinitialization",flush=True)
try:
    mtk.port.close(reset=True)
finally:
    print("Transport reset attempted. Check physical display, USB, ADB and Fastboot.",flush=True)
