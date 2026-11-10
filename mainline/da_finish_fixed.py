#!/usr/bin/env python3
"""ASUS Z301ML: finish existing LEGACY Download Agent to HOME_SCREEN.

Fixes MTKClient upstream DALegacy.finish() ACK type bug:
usbread(1)[0] returns int; Rsp.ACK is bytes b'\x5a', so 'ack is Rsp.ACK'
can never pass. This diagnostic sends the correct finish bytes.
No eMMC writes, no partitions altered.
"""
import os,sys,time,json,hashlib,subprocess,signal,logging
from pathlib import Path
from struct import pack
HOME=Path('/Users/matveysazhnov')
MTK=HOME/'mtkclient'
ROOT=HOME/'ASUS-Z301ML-port/mainline'
WORK=ROOT/'recovery-readcheck'
STOCK=HOME/'ASUS-Z301ML-backup/recovery.bin'
EXP=HOME/'ASUS-Z301ML-port/output/z301ml-test-recovery-318-FULL16MiB-UNSIGNED-DO_NOT_FLASH.img'
READBACK=WORK/'recovery-live-after-flash.bin'
HEAD=WORK/'da-live-header-check.bin'
STATE=MTK/'.state'
S_STOCK='7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e'
S_EXP='e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2'
def check(v,text):
    if not v: raise RuntimeError('STOP: '+text)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def watchdog(signum,frame):
    print('TIMEOUT: USB operation did not complete; no memory writes were issued',flush=True)
    os._exit(124)
signal.signal(signal.SIGALRM,watchdog)
for p,h in ((STOCK,S_STOCK),(EXP,S_EXP),(READBACK,S_EXP)):
    check(p.is_file() and p.stat().st_size==16777216 and sha(p)==h,'hash/size mismatch '+str(p))
check(STATE.is_file(),'MTK DA state missing')
s=json.loads(STATE.read_text())
check(s.get('hwcode')==0x321 and s.get('meid')=='e38fd44f882d91c96dfa77e29b2cc032','Device MEID mismatch')
check(s.get('flashmode')=='LEGACY','Not Legacy DA')
usb=subprocess.run(['ioreg','-p','IOUSB','-l','-w0'],capture_output=True,text=True,timeout=7,check=True).stdout
check('"idVendor" = 3725' in usb and '"idProduct" = 8193' in usb,'Not connected as DA 0e8d:2001')
print('PASS: active DA, device MEID, original recovery, and experimental readback verified',flush=True)
if '--check' in sys.argv:
    print('DRY RUN: no commands sent to USB');sys.exit(0)
check(os.geteuid()==0,'Requires sudo for direct USB')
check(not HEAD.exists(),'DA header output already exists; inspect existing file before retrying')
signal.alarm(35)
sys.modules['mfusepy']=None
sys.path.insert(0,str(MTK))
os.chdir(MTK)
from mtkclient.config.mtk_config import MtkConfig
from mtkclient.Library.mtk_class import Mtk
from mtkclient.Library.DA.mtk_da_handler import DaHandler
from mtkclient.Library.Partitions.gpt import GptSettings
cfg=MtkConfig(loglevel=logging.INFO)
cfg.gpt_settings=GptSettings(0,0,0)
mtk=Mtk(config=cfg,loglevel=logging.INFO)
da=DaHandler(mtk,logging.INFO)
print('Reopening EXISTING legacy DA, without BROM handshake...',flush=True)
mtk=da.connect(mtk,directory='.')
check(mtk is not None and mtk.reinited,'DA did not resume')
mtk=da.configure_da(mtk)
check(mtk is not None and mtk.config.hwcode==0x321,'Wrong DA chipset')
print('READ-ONLY DA command-loop check, 4096 bytes from recovery...',flush=True)
ok=mtk.daloader.readflash(addr=0x5d80000,length=4096,filename=str(HEAD),parttype='user')
check(ok and HEAD.is_file() and HEAD.stat().st_size==4096,'DA did not return recovery header; no FINISH command sent')
check(HEAD.read_bytes()==EXP.read_bytes()[:4096],'Recovery head differs from verified experimental image')
print('PASS: Legacy DA is responsive. Recovery header matches test kernel.',flush=True)

print('Sending FINISH_CMD 0xD9 using correct ACK comparison',flush=True)
dal=mtk.daloader.da
cmd=dal.Cmd.FINISH_CMD
assert cmd==b'\xd9'
writeok=dal.usbwrite(cmd)
print('FINISH_CMD write:',writeok,flush=True)
ack=dal.usbread(1)
print('FINISH_CMD ACK:',repr(ack),flush=True)
check(ack==b'\x5a','DA did not acknowledge FINISH_CMD')
print('ACK 5A confirmed. Sending bootmode HOME_SCREEN=1 as big-endian uint32.',flush=True)
writeok=dal.usbwrite(pack('>I',1))
print('HOME_SCREEN mode payload write:',writeok,flush=True)
ack=dal.usbread(1)
print('HOME_SCREEN ACK:',repr(ack),flush=True)
if ack==b'\x5a':
    print('SUCCESS: DA accepted HOME_SCREEN boot command.',flush=True)
else:
    print('WARNING: final ACK absent or unexpected (device may already be rebooting).',flush=True)
try:mtk.port.close(reset=False)
except Exception as e:print('USB close:',repr(e),flush=True)
print('FINISH sequence complete. Watch for Android USB/ADB or physical boot screen.',flush=True)
