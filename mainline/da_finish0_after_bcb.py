#!/usr/bin/env python3
"""ASUS Z301ML: exit existing Legacy DA using NORMAL (0) after BCB backup/write.
Only reads 512 bytes from para and issues DA FINISH_CMD. No eMMC writes.
"""
import os,sys,hashlib,subprocess,json,logging
from pathlib import Path
H=Path("/Users/matveysazhnov");MTK=H/"mtkclient"
W=H/"ASUS-Z301ML-port/mainline/recovery-readcheck"
PARA=W/"para-after-boot-recovery-guard.bin"
PRE=W/"para-before-boot-recovery-guard.bin"
CMD=W/"para-boot-recovery-sector-512-PREPARED-NOT-FLASHED.bin"
READ=W/"para-boot-recovery-confirm-before-finish0.bin"
STATE=MTK/".state"
def ck(q,s):
 if not q:raise RuntimeError("STOP: "+s)
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ck(not READ.exists(),"preflight output exists")
 for p,size in ((PARA,524288),(PRE,524288),(CMD,512)):
  ck(p.is_file() and p.stat().st_size==size,"missing/incorrect "+str(p))
 p=PARA.read_bytes();orig=PRE.read_bytes();cmd=CMD.read_bytes()
 ck(sha(p)=="5b621a57fcd12644e542f2aab563e2b00289ff4bd38c0bed0ba6236c47a28680","para after SHA mismatch")
 ck(p==cmd+orig[512:],"para modified beyond bootloader command")
 ck(p[:32]==b"boot-recovery"+bytes(19),"boot-recovery command missing")
 ck(sha(orig)=="25464b97ab1d4790bab32a580de8e06649d9985deba118e1415a368fcd0e45f3","original para backup changed")
 s=json.loads(STATE.read_text())
 ck(s.get("meid")=="e38fd44f882d91c96dfa77e29b2cc032" and s.get("hwcode")==0x321 and s.get("flashmode")=="LEGACY","wrong active device")
 u=subprocess.run(["ioreg","-p","IOUSB","-l","-w0"],capture_output=True,text=True,timeout=8).stdout
 ck('"idVendor" = 3725' in u and '"idProduct" = 8193' in u,"DA USB 0e8d:2001 missing")
 print("PREFLIGHT PASS: backed-up PARA + BCB boot-recovery + DA hardware identity; no writes",flush=True)
 if "--check" in sys.argv:
  print("DRYRUN: no USB/eMMC command issued",flush=True);return
 ck(os.geteuid()==0,"sudo -n required")
 os.chdir(MTK);sys.path.insert(0,str(MTK));sys.modules["mfusepy"]=None
 from mtkclient.config.mtk_config import MtkConfig
 from mtkclient.Library.mtk_class import Mtk
 from mtkclient.Library.DA.mtk_da_handler import DaHandler
 from mtkclient.Library.Partitions.gpt import GptSettings
 cfg=MtkConfig(loglevel=logging.INFO);cfg.gpt_settings=GptSettings(0,0,0)
 mtk=Mtk(config=cfg,loglevel=logging.INFO);da=DaHandler(mtk,logging.INFO)
 print("Reopening existing stage2 DA, no BROM handshake",flush=True)
 mtk=da.connect(mtk,directory=".")
 ck(mtk is not None and mtk.reinited,"DA cannot resume")
 mtk=da.configure_da(mtk)
 ck(mtk is not None and mtk.daloader.patch and mtk.config.hwcode==0x321,"wrong DA")
 found,part=mtk.daloader.detect_partition("para",parttype="user")
 ck(found and part.sector==157696 and part.sectors==1024,"para GPT geometry mismatch")
 addr=part.sector*512
 ck(addr==0x4d00000,"para offset mismatch")
 print("Confirming live para BCB sector before DA exit",flush=True)
 ck(mtk.daloader.readflash(addr=addr,length=512,filename=str(READ),parttype="user"),"read failed")
 ck(READ.stat().st_size==512 and READ.read_bytes()==cmd,"LIVE BCB sector no longer matches expected; no FINISH")
 print("PASS: BCB boot-recovery visible LIVE in eMMC (512 bytes)",flush=True)
 print("Sending corrected DALegacy.finish(0) [NORMAL mode], no write commands",flush=True)
 ok=mtk.daloader.da.finish(0)
 print("FINISH(0) ACK:",ok,flush=True)
 ck(ok,"DA did not ACK finish(0); KEEP CONNECTED")
 try:mtk.port.close(reset=True)
 except Exception as e:print("USB transport close/reset:",repr(e),flush=True)
 print("DA FINISH(0) accepted; USB transport reset/close requested. Monitor live USB.",flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:print("STOPPED:",repr(e),flush=True);sys.exit(1)
