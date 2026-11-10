#!/usr/bin/env python3
"""One-sector restore of factory para BCB, only after confirmed Z301ML DA.
Use ONLY if boot-recovery loops. Reverses exactly the 13-byte command patch.
No boot/recovery/LK/GPT writes.
"""
import hashlib,os,sys,json,logging,subprocess
from pathlib import Path
H=Path('/Users/matveysazhnov')
MTK=H/'mtkclient'
W=H/'ASUS-Z301ML-port/mainline/recovery-readcheck'
ORIGINAL=W/'para-original-sector-512-guard.bin'
ORIGINAL_PARA=W/'para-before-boot-recovery-guard.bin'
PATCHED_PARA=W/'para-after-boot-recovery-guard.bin'
BEFORE=W/'para-before-BCB-restore.bin'
AFTER=W/'para-after-BCB-restore.bin'
STOCK_SHA='25464b97ab1d4790bab32a580de8e06649d9985deba118e1415a368fcd0e45f3'
PATCH_SHA='5b621a57fcd12644e542f2aab563e2b00289ff4bd38c0bed0ba6236c47a28680'
MEID='e38fd44f882d91c96dfa77e29b2cc032'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(v,msg):
 if not v:raise RuntimeError('SAFETY STOP: '+msg)
def main():
 for path,length,h in ((ORIGINAL,512,None),(ORIGINAL_PARA,524288,STOCK_SHA),(PATCHED_PARA,524288,PATCH_SHA)):
  ck(path.is_file() and path.stat().st_size==length,'bad file '+str(path))
  if h:ck(sha(path)==h,'bad archive digest '+str(path))
 ck(ORIGINAL.read_bytes()==ORIGINAL_PARA.read_bytes()[:512],'saved original sector differs')
 ck(PATCHED_PARA.read_bytes()[512:]==ORIGINAL_PARA.read_bytes()[512:],'unexpected para changes beyond sector 0')
 ck(not BEFORE.exists() and not AFTER.exists(),'restore output exists')
 s=json.loads((MTK/'.state').read_text())
 ck(s.get('flashmode')=='LEGACY' and s.get('hwcode')==0x321 and s.get('meid')==MEID,'DA state mismatches')
 u=subprocess.run(['ioreg','-p','IOUSB','-l','-w0'],capture_output=True,text=True,timeout=7).stdout
 ck('"idVendor" = 3725' in u and '"idProduct" = 8193' in u,'USB DA 0e8d:2001 unavailable')
 print('RESTORE PREFLIGHT PASS',flush=True)
 if '--check' in sys.argv:print('DRYRUN, NO DEVICE COMMANDS',flush=True);return
 ck(os.geteuid()==0,'root needed')
 os.chdir(MTK);sys.path.insert(0,str(MTK));sys.modules['mfusepy']=None
 from mtkclient.config.mtk_config import MtkConfig
 from mtkclient.Library.mtk_class import Mtk
 from mtkclient.Library.DA.mtk_da_handler import DaHandler
 from mtkclient.Library.Partitions.gpt import GptSettings
 cfg=MtkConfig(loglevel=logging.INFO);cfg.gpt_settings=GptSettings(0,0,0)
 mtk=Mtk(config=cfg,loglevel=logging.INFO);da=DaHandler(mtk,logging.INFO)
 mtk=da.connect(mtk,directory='.')
 ck(mtk is not None and mtk.reinited,'could not reattach DA')
 mtk=da.configure_da(mtk)
 ck(mtk is not None and mtk.daloader.patch and mtk.config.hwcode==0x321,'wrong DA chipset')
 found,part=mtk.daloader.detect_partition('para',parttype='user')
 ck(found and part.sector==157696 and part.sectors==1024,'GPT para mismatch')
 addr=part.sector*512;ck(addr==0x04d00000,'offset mismatch')
 ck(mtk.daloader.readflash(addr=addr,length=524288,filename=str(BEFORE),parttype='user'),'before read fail')
 ck(BEFORE.stat().st_size==524288,'read truncated')
 h=sha(BEFORE)
 ck(h in (STOCK_SHA,PATCH_SHA),'para contains unknown state; refuse restore')
 if h==STOCK_SHA:
  print('Already restored; no eMMC writes.',flush=True);return
 print('Restoring original 512-byte first sector of para',flush=True)
 ck(mtk.daloader.writeflash(addr=addr,length=512,filename=str(ORIGINAL),parttype='user'),'restore write failed')
 ck(mtk.daloader.readflash(addr=addr,length=524288,filename=str(AFTER),parttype='user'),'postread fail')
 ck(AFTER.stat().st_size==524288 and sha(AFTER)==STOCK_SHA,'restore FULL PARA SHA mismatch')
 print('SUCCESS: original para completely recovered; boot unchanged.',flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:print('STOPPED',repr(e),flush=True);sys.exit(1)
