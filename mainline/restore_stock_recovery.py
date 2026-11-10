#!/usr/bin/env python3
"""ASUS Z301ML: restore ONLY stock recovery with live GPT+hash checks.
Use only if experimental recovery fails and device is in Legacy DA 0e8d:2001.
"""
import os,sys,hashlib,json,subprocess,logging
from pathlib import Path
H=Path("/Users/matveysazhnov")
MTK=H/"mtkclient"
W=H/"ASUS-Z301ML-port/mainline/recovery-readcheck"
STATE=MTK/".state"
STOCK=H/"ASUS-Z301ML-backup/recovery.bin"
EXPERIMENT=H/"ASUS-Z301ML-port/output/z301ml-test-recovery-318-FULL16MiB-UNSIGNED-DO_NOT_FLASH.img"
CURRENT=W/"recovery-restore-before.bin"
AFTER=W/"recovery-restore-after.bin"
N=16777216
STOCK_SHA="7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e"
EXP_SHA="e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2"
def check(ok,msg):
    if not ok:raise RuntimeError("SAFETY STOP: "+msg)
def hash(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in [(STOCK,STOCK_SHA),(EXPERIMENT,EXP_SHA)]:
    check(p.is_file() and p.stat().st_size==N and hash(p)==h,"image changed: "+str(p))
for p in (CURRENT,AFTER):check(not p.exists(),"output exists: "+str(p))
check(STATE.is_file(),"No DA state; first establish download agent")
s=json.loads(STATE.read_text())
check(s.get("hwcode")==0x321 and s.get("meid")=="e38fd44f882d91c96dfa77e29b2cc032" and s.get("flashmode")=="LEGACY","Wrong device/state")
usb=subprocess.run(["ioreg","-p","IOUSB","-l","-w0"],capture_output=True,text=True,timeout=8,check=True).stdout
check('"idVendor" = 3725' in usb and '"idProduct" = 8193' in usb,"USB is not in legacy DA mode")
print("PRECHECK PASS: original recovery verified; target matches DA MEID",flush=True)
if "--check" in sys.argv: print("DRY-RUN: no eMMC operations sent");sys.exit(0)
check(os.geteuid()==0,"sudo required")
os.chdir(MTK);sys.path.insert(0,str(MTK));sys.modules["mfusepy"]=None
from mtkclient.Library.mtk_class import Mtk
from mtkclient.Library.DA.mtk_da_handler import DaHandler
from mtkclient.config.mtk_config import MtkConfig
from mtkclient.Library.Partitions.gpt import GptSettings
cfg=MtkConfig(loglevel=logging.INFO);cfg.gpt_settings=GptSettings(0,0,0)
mtk=Mtk(config=cfg,loglevel=logging.INFO); da=DaHandler(mtk,logging.INFO)
mtk=da.connect(mtk,directory=".")
check(mtk is not None and mtk.reinited,"Could not reattach to existing DA")
mtk=da.configure_da(mtk)
check(mtk is not None and mtk.daloader.patch,"DA patch state invalid")
present,part=mtk.daloader.detect_partition("recovery",parttype="user")
check(present and part.sector==191488 and part.sectors==32768,"recovery GPT differs")
offset=part.sector*512
check(mtk.daloader.readflash(addr=offset,length=N,filename=str(CURRENT),parttype="user"),"pre-read error")
check(CURRENT.is_file() and CURRENT.stat().st_size==N,"read length mismatch")
live=hash(CURRENT)
print("CURRENT RECOVERY SHA256",live,flush=True)
check(live in [STOCK_SHA,EXP_SHA],"unexpected recovery contents: refuse write")
if live==STOCK_SHA:
    print("Already stock recovery: no write required",flush=True);sys.exit(0)
print("Restoring factory recovery ONLY to recovery partition",flush=True)
check(mtk.daloader.writeflash(addr=offset,length=N,filename=str(STOCK),parttype="user"),"write failed")
check(mtk.daloader.readflash(addr=offset,length=N,filename=str(AFTER),parttype="user"),"post-read failed")
check(AFTER.is_file() and AFTER.stat().st_size==N and hash(AFTER)==STOCK_SHA,"RESTORE NOT VERIFIED")
print("SUCCESS: stock recovery restored and readback SHA256 verified. Boot untouched.",flush=True)
