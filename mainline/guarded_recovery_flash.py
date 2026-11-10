#!/usr/bin/env python3
"""ASUS Z301ML: guarded recovery-only experimental kernel flash via *existing* DA.
Only writes the 16 MiB GPT 'recovery' partition and only after reading + hashing
that exact partition against the known-good ASUS stock backup.
Restores stock recovery automatically on post-write mismatch when transport survives.
Never touches boot, preloader, nvram, nvdata, lk, GPT, or other partitions.
"""
import hashlib, json, logging, os, runpy, subprocess, sys, time
from pathlib import Path

HOME=Path("/Users/matveysazhnov")
MTK=HOME/"mtkclient"
WORK=HOME/"ASUS-Z301ML-port/mainline/recovery-readcheck"
BACKUP=HOME/"ASUS-Z301ML-backup/recovery.bin"
PREVIOUS=WORK/"recovery-from-device.bin"
IMAGE=HOME/"ASUS-Z301ML-port/output/z301ml-test-recovery-318-FULL16MiB-UNSIGNED-DO_NOT_FLASH.img"
BEFORE=WORK/"recovery-live-before-flash.bin"
AFTER=WORK/"recovery-live-after-flash.bin"
RESTORED=WORK/"recovery-restored-after-failure.bin"
STATE=MTK/".state"
PARTSIZE=16*1024*1024
STOCK_HASH="7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e"
IMAGE_HASH="e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2"
EXPECTED_MEID="e38fd44f882d91c96dfa77e29b2cc032"
EXPECTED_SECTOR=191488
EXPECTED_SECTORS=32768

def check(test, reason):
    if not test: raise RuntimeError("SAFETY STOP: "+reason)

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as inp:
        for block in iter(lambda:inp.read(1<<20),b""):h.update(block)
    return h.hexdigest()

def preflight():
    WORK.mkdir(parents=True,exist_ok=True)
    for p, expected in ((BACKUP,STOCK_HASH),(PREVIOUS,STOCK_HASH),(IMAGE,IMAGE_HASH)):
        check(p.is_file(),f"missing {p}")
        check(p.stat().st_size==PARTSIZE,f"unexpected file length {p}")
        check(digest(p)==expected,f"hash mismatch {p}")
        print("PASS",str(p),"SHA256",expected,flush=True)
    check(IMAGE.read_bytes()[:8]==b"ANDROID!","experimental image invalid header")
    for p in (BEFORE,AFTER,RESTORED):
        check(not p.exists(),f"output already exists: {p}")
    check(STATE.is_file(),"DA state missing: DO NOT retry BROM automatically")
    state=json.loads(STATE.read_text())
    check(state.get("flashmode")=="LEGACY" and state.get("patched") is True and state.get("hwcode")==0x321,"Unexpected MTK DA state")
    check(state.get("meid","").lower()==EXPECTED_MEID,"Wrong physical device (MEID)")
    check(state.get("m_emmc_ua_size")==31268536320,"Unexpected eMMC geometry")
    usb=subprocess.run(["ioreg","-p","IOUSB","-l","-w0"],capture_output=True,text=True,timeout=8,check=True).stdout
    check('"idVendor" = 3725' in usb and '"idProduct" = 8193' in usb,"Target not connected in Legacy Download Agent mode 0e8d:2001")
    print("PASS: active patched DA USB mode 0e8d:2001 and matching stored MEID",flush=True)

def main():
    preflight()
    if "--check" in sys.argv:
        print("DRY RUN PASS: no USB claimed, no eMMC commands",flush=True);return
    check(os.geteuid()==0,"run as root via sudo")
    sys.modules["mfusepy"]=None
    os.chdir(MTK)
    sys.path.insert(0, str(MTK))  # Script directory is not the MTKClient source root.
    from mtkclient.config.mtk_config import MtkConfig
    from mtkclient.Library.mtk_class import Mtk
    from mtkclient.Library.DA.mtk_da_handler import DaHandler
    from mtkclient.Library.Partitions.gpt import GptSettings
    config=MtkConfig(loglevel=logging.INFO)
    config.gpt_settings=GptSettings(0,0,0)
    mtk=Mtk(config=config,loglevel=logging.INFO)
    da=DaHandler(mtk,logging.INFO)
    print("Connecting to EXISTING stage2 DA (no BROM handshake)...",flush=True)
    mtk=da.connect(mtk,directory=".")
    check(mtk is not None and mtk.reinited,"Existing DA session not reused; STOP")
    mtk=da.configure_da(mtk)
    check(mtk is not None and mtk.daloader.patch,"Unexpected DA state; STOP")
    check(mtk.config.hwcode==0x321,"Wrong chipset")
    found, part=mtk.daloader.detect_partition("recovery",parttype="user")
    check(found,"No GPT recovery partition")
    check(part.sector==EXPECTED_SECTOR and part.sectors==EXPECTED_SECTORS,"GPT recovery geometry mismatch")
    addr=part.sector*512
    length=part.sectors*512
    check(addr==0x5d80000 and length==PARTSIZE,"Incorrect recovery region")
    print("PASS: GPT recovery",hex(addr),hex(length),flush=True)
    print("Pre-reading recovery in SAME DA session...",flush=True)
    read=mtk.daloader.readflash(addr=addr,length=length,filename=str(BEFORE),parttype="user")
    check(read and BEFORE.is_file() and BEFORE.stat().st_size==length,"Live recovery read failed")
    check(digest(BEFORE)==STOCK_HASH,"Live recovery has changed since backup; REFUSE TO FLASH")
    print("PASS: LIVE recovery backup SHA256 matches original; ready to flash only recovery",flush=True)
    print("WRITING EXPERIMENTAL 3.18.35 RECOVERY (16MiB); boot partition untouched",flush=True)
    wrote=mtk.daloader.writeflash(addr=addr,length=length,filename=str(IMAGE),parttype="user")
    if not wrote:
        print("WARNING: MTKClient reported write failure. Trying to restore stock recovery.",flush=True)
        restore(mtk,addr,length)
        raise RuntimeError("WRITE REPORTED FAILURE. Stock restore attempted.")
    print("POST-WRITE READBACK...",flush=True)
    try:
        check(mtk.daloader.readflash(addr=addr,length=length,filename=str(AFTER),parttype="user"),
              "post-write read failed")
        check(AFTER.is_file() and AFTER.stat().st_size==length,"post-write readback file wrong size")
        check(digest(AFTER)==IMAGE_HASH,"post-write SHA256 mismatch")
    except Exception:
        print("ERROR: experimental image failed readback; trying stock restore",flush=True)
        restore(mtk,addr,length)
        raise
    print("SUCCESS: experimental 3.18.35 kernel flashed ONLY into recovery; SHA256 readback verified",flush=True)
    print("Boot partition is untouched. Device has not been rebooted. Stock recovery backup preserved.",flush=True)

def restore(mtk,addr,length):
    ok=mtk.daloader.writeflash(addr=addr,length=length,filename=str(BACKUP),parttype="user")
    if not ok:
        print("CRITICAL: stock recovery restore write failed. Keep device connected.",flush=True)
        return False
    if mtk.daloader.readflash(addr=addr,length=length,filename=str(RESTORED),parttype="user"):
        if RESTORED.is_file() and RESTORED.stat().st_size==length and digest(RESTORED)==STOCK_HASH:
            print("RESTORE VERIFIED: original stock recovery restored.",flush=True);return True
    print("CRITICAL: stock restore readback not verified; do not unplug.",flush=True)
    return False

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("STOPPED:",repr(exc),flush=True)
        sys.exit(1)
