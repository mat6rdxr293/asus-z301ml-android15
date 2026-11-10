#!/usr/bin/env python3
"""Read-only Z301ML live Recovery (16MiB) and para (512KiB) from existing DA.
No USB reboot, no writes. Keep DA attached after script exit.
"""
from pathlib import Path
import os,sys,hashlib,json,subprocess,runpy
ROOT=Path("/Users/matveysazhnov")
MTK=ROOT/"mtkclient"
WORK=ROOT/"ASUS-Z301ML-port/mainline/recovery-readcheck"
REC=WORK/"live-recovery-1800.bin"
PARA=WORK/"live-para-backup-1800.bin"
EXPECT="e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2"
STOCK="7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e"
def ck(x,msg):
 if not x:raise RuntimeError("STOP: "+msg)
for p in (REC,PARA):
 ck(not p.exists(),"file exists, never overwrite "+str(p))
state=json.loads((MTK/".state").read_text())
ck(state.get("hwcode")==0x321 and state.get("meid")=="e38fd44f882d91c96dfa77e29b2cc032" and state.get("flashmode")=="LEGACY", "wrong DA state")
usb=subprocess.run(["ioreg","-p","IOUSB","-l","-w0"],text=True,capture_output=True,timeout=7).stdout
ck('"idVendor" = 3725' in usb and '"idProduct" = 8193' in usb,"not connected as 0e8d:2001")
ck(os.geteuid()==0,"requires sudo")
os.chdir(MTK)
sys.path.insert(0,str(MTK))
sys.modules["mfusepy"]=None
sys.argv=["mtk.py","r","recovery,para",f"{REC},{PARA}"]
print("READ-ONLY MTKClient existing DA: recovery,para",flush=True)
try:runpy.run_path("mtk.py",run_name="__main__")
except SystemExit as e:
 if e.code not in (0,None):
  raise
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,size in ((REC,16777216),(PARA,524288)):
 ck(p.exists() and p.stat().st_size==size,f"bad readback size {p}")
 print(f"READBACK {p.name}: size={size} sha256={digest(p)}",flush=True)
h=digest(REC)
print("RECOVERY_EXPECTED_MATCH",h==EXPECT,flush=True)
print("RECOVERY_STOCK_MATCH",h==STOCK,flush=True)
if h not in (EXPECT,STOCK):
 print("STOP: Unrecognized recovery! DO NOT WRITE.")
else:
 print("GOOD: known recovery hash verified. PARA backup saved. NO WRITES.",flush=True)
