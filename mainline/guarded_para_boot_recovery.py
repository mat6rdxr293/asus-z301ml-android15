#!/usr/bin/env python3
"""Guarded ASUS P00L para boot-recovery BCB sector write; exact backup/readback.
Only writes 512-byte FIRST SECTOR of GPT para at 0x04d00000. Never boot.
Do not reset/reboot device. Reads complete para before & after.
"""
import os,sys,logging,hashlib,subprocess,json
from pathlib import Path
H=Path('/Users/matveysazhnov')
MTK=H/'mtkclient'
W=H/'ASUS-Z301ML-port/mainline/recovery-readcheck'
PRE=W/'live-para-backup-1800.bin'
PRE_REC=W/'live-recovery-1800.bin'
CMD=W/'para-boot-recovery-sector-512-PREPARED-NOT-FLASHED.bin'
BEFORE=W/'para-before-boot-recovery-guard.bin'
AFTER=W/'para-after-boot-recovery-guard.bin'
RESTORED=W/'para-restored-if-error-guard.bin'
ORIGINAL_SECTOR=W/'para-original-sector-512-guard.bin'
STATE=MTK/'.state'
PARA_SHA='25464b97ab1d4790bab32a580de8e06649d9985deba118e1415a368fcd0e45f3'
REC_SHA='e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2'
CMD_SHA='9418492e5b413376d2927de020eecc19a0be271687c4edb6437b7ce7268a2171'
MEID='e38fd44f882d91c96dfa77e29b2cc032'
SECTOR=157696
COUNT=1024
LENGTH=COUNT*512
def ck(v,msg):
    if not v:raise RuntimeError('SAFETY STOP: '+msg)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def sanity():
    for p,size,hash_ in [(PRE,LENGTH,PARA_SHA),(PRE_REC,16777216,REC_SHA),(CMD,512,CMD_SHA)]:
        ck(p.is_file() and p.stat().st_size==size,'file missing/wrong length: '+str(p))
        ck(sha(p)==hash_,'SHA256 mismatch: '+str(p))
    p=PRE.read_bytes();c=CMD.read_bytes()
    ck(p[:512].startswith(bytes(32)),'para BCB field is not blank')
    ck(c[:32]==b'boot-recovery'+bytes(19),'unexpected BCB command')
    ck(c[32:]==p[32:512],'prepared sector modifies more than command[32]')
    for output in (BEFORE,AFTER,RESTORED,ORIGINAL_SECTOR):
        ck(not output.exists(),'output already exists: '+str(output))
    s=json.loads(STATE.read_text())
    ck(s.get('hwcode')==0x321 and s.get('flashmode')=='LEGACY' and s.get('patched') is True
       and s.get('meid')==MEID and s.get('m_emmc_ua_size')==31268536320,
       'device state mismatch')
    u=subprocess.run(['ioreg','-p','IOUSB','-l','-w0'],capture_output=True,text=True,timeout=7,check=True).stdout
    ck('"idVendor" = 3725' in u and '"idProduct" = 8193' in u,'legacy DA USB 0e8d:2001 not present')
    print('PRECHECK PASS: confirmed MEID / DA / original para and recovery / 512-byte command',flush=True)
def restore(mtk,addr):
    print('Attempting restore of ORIGINAL 512-byte para sector only',flush=True)
    ok=mtk.daloader.writeflash(addr=addr,length=512,filename=str(ORIGINAL_SECTOR),parttype='user')
    ck(ok,'CRITICAL: original para sector write failed; keep device connected')
    ok=mtk.daloader.readflash(addr=addr,length=LENGTH,filename=str(RESTORED),parttype='user')
    ck(ok and RESTORED.exists() and RESTORED.stat().st_size==LENGTH,'CRITICAL: restore readback failed')
    ck(sha(RESTORED)==PARA_SHA,'CRITICAL: restore SHA mismatch')
    print('RESTORED ORIGINAL PARA AND VERIFIED WHOLE 512 KIB SHA256',flush=True)
def main():
    sanity()
    if '--check' in sys.argv:
        print('DRY RUN PASS: 0 bytes written',flush=True)
        return
    ck(os.geteuid()==0,'sudo -n full interpreter path required')
    sys.modules['mfusepy']=None
    os.chdir(MTK);sys.path.insert(0,str(MTK))
    from mtkclient.config.mtk_config import MtkConfig
    from mtkclient.Library.mtk_class import Mtk
    from mtkclient.Library.DA.mtk_da_handler import DaHandler
    from mtkclient.Library.Partitions.gpt import GptSettings
    cfg=MtkConfig(loglevel=logging.INFO);cfg.gpt_settings=GptSettings(0,0,0)
    mtk=Mtk(config=cfg,loglevel=logging.INFO)
    da=DaHandler(mtk,logging.INFO)
    print('Reusing existing patched legacy DA, NO BROM handshake...',flush=True)
    mtk=da.connect(mtk,directory='.')
    ck(mtk is not None and mtk.reinited,'DA resume failed')
    mtk=da.configure_da(mtk)
    ck(mtk is not None and mtk.daloader.patch and mtk.config.hwcode==0x321,'wrong DA/CPU')
    found,part=mtk.daloader.detect_partition('para',parttype='user')
    ck(found and part.sector==SECTOR and part.sectors==COUNT,'GPT para offset/length mismatch')
    addr=part.sector*512
    ck(addr==0x04d00000 and LENGTH==0x80000,'para bounds wrong')
    print(f'PASS: live GPT para at {addr:#x} length {LENGTH:#x}',flush=True)
    ck(mtk.daloader.readflash(addr=addr,length=LENGTH,filename=str(BEFORE),parttype='user'),
        'live para pre-read failed')
    ck(BEFORE.is_file() and BEFORE.stat().st_size==LENGTH and sha(BEFORE)==PARA_SHA,
       'LIVE PARA differs from backed-up para; refuse write')
    ck(BEFORE.read_bytes()[:512]==PRE.read_bytes()[:512],
       'first para sector differs from backup')
    ORIGINAL_SECTOR.write_bytes(PRE.read_bytes()[:512])
    ck(ORIGINAL_SECTOR.stat().st_size==512,'original 512-byte sector backup failed')
    print('PASS: LIVE para 512KiB matches archived pre-write SHA256; original sector saved',flush=True)
    print('WRITE ONLY 512 BYTES OF PARA (bootloader_message.command @ relative offset 0)',flush=True)
    ok=mtk.daloader.writeflash(addr=addr,length=512,filename=str(CMD),parttype='user')
    if not ok:
        print('WARNING: DA write did not ACK correctly; restoring first sector',flush=True)
        restore(mtk,addr)
        raise RuntimeError('write failed; original para restored')
    try:
        ck(mtk.daloader.readflash(addr=addr,length=LENGTH,filename=str(AFTER),parttype='user'),
           'live para post-read failed')
        ck(AFTER.exists() and AFTER.stat().st_size==LENGTH,'post-read full para missing/wrong size')
        expect=CMD.read_bytes()+PRE.read_bytes()[512:]
        real=AFTER.read_bytes()
        ck(real==expect,'post-read does not match 512-byte BCB patch ONLY')
        ck(real[0:32]==b'boot-recovery'+bytes(19),'command not correct')
    except BaseException:
        print('CRITICAL post-read verification failure; restoring original para sector',flush=True)
        restore(mtk,addr)
        raise
    print('SUCCESS: para[0:32] = boot-recovery (NUL padded)',flush=True)
    print('POSTWRITE SHA256',sha(AFTER),'readback fully verified, other 524275 bytes unchanged',flush=True)
    print('Recovery 3.18.35 previously verified. boot/lk/GPT/other partitions untouched.',flush=True)
    print('Still connected in DA, not rebooted.',flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        print('STOPPED:',repr(e),flush=True)
        sys.exit(1)
