#!/usr/bin/env python3
"""Guarded write of a 16 MiB image into the RECOVERY partition only (existing legacy DA).
Usage: sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u flash_recovery_image.py IMAGE [--check]
Pre-read must equal stock or a known previous test image; post-read must equal IMAGE.
"""
import os, sys, hashlib, json, subprocess, logging, time
from pathlib import Path

H = Path('/Users/matveysazhnov'); MTK = H / 'mtkclient'
W = H / 'ASUS-Z301ML-port/mainline/recovery-readcheck'
N = 16777216
KNOWN = {
    '7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e': 'stock recovery',
    'e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2': 'test 3.18.35 (gcc15)',
    '3b260803465d1ab886bdccd1f27fecb757cef02a2ffc91d5741fc78a61f84959': 'linux7 v2 gadget',
}


def ck(v, m):
    if not v:
        raise RuntimeError('SAFETY STOP: ' + m)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    img = Path(sys.argv[1]).resolve()
    ck(img.is_file() and img.stat().st_size == N, 'image must be exactly 16 MiB')
    ck(Path(img).read_bytes()[:8] == b'ANDROID!', 'not an Android boot image')
    want = sha(img)
    print('IMAGE', img.name, want, KNOWN.get(want, 'NEW'), flush=True)
    s = json.loads((MTK / '.state').read_text())
    ck(s.get('hwcode') == 0x321 and s.get('meid') == 'e38fd44f882d91c96dfa77e29b2cc032' and s.get('flashmode') == 'LEGACY', 'state')
    u = subprocess.run(['ioreg', '-p', 'IOUSB', '-l', '-w0'], capture_output=True, text=True, timeout=8).stdout
    ck('"idVendor" = 3725' in u and '"idProduct" = 8193' in u, 'DA 0e8d:2001 not present')
    print('PRECHECK PASS', flush=True)
    if '--check' in sys.argv:
        print('DRY RUN'); return
    ck(os.geteuid() == 0, 'sudo')
    ts = time.strftime('%H%M%S')
    pre, post = W / f'recovery-pre-{ts}.bin', W / f'recovery-post-{ts}.bin'
    os.chdir(MTK); sys.path.insert(0, str(MTK)); sys.modules['mfusepy'] = None
    from mtkclient.config.mtk_config import MtkConfig
    from mtkclient.Library.mtk_class import Mtk
    from mtkclient.Library.DA.mtk_da_handler import DaHandler
    from mtkclient.Library.Partitions.gpt import GptSettings
    cfg = MtkConfig(loglevel=logging.INFO); cfg.gpt_settings = GptSettings(0, 0, 0)
    mtk = Mtk(config=cfg, loglevel=logging.INFO); da = DaHandler(mtk, logging.INFO)
    mtk = da.connect(mtk, directory='.'); ck(mtk is not None and mtk.reinited, 'DA resume')
    mtk = da.configure_da(mtk); ck(mtk.daloader.patch and mtk.config.hwcode == 0x321, 'DA')
    ok, part = mtk.daloader.detect_partition('recovery', parttype='user')
    ck(ok and part.sector == 191488 and part.sectors == 32768, 'recovery GPT mismatch')
    addr = part.sector * 512
    ck(mtk.daloader.readflash(addr=addr, length=N, filename=str(pre), parttype='user'), 'pre-read')
    cur = sha(pre)
    print('CURRENT', cur, KNOWN.get(cur, 'UNKNOWN'), flush=True)
    ck(cur in KNOWN, 'unknown current recovery; refuse')
    if cur == want:
        print('Already flashed; nothing to do'); return
    print('WRITING recovery...', flush=True)
    ck(mtk.daloader.writeflash(addr=addr, length=N, filename=str(img), parttype='user'), 'write')
    ck(mtk.daloader.readflash(addr=addr, length=N, filename=str(post), parttype='user'), 'post-read')
    ck(sha(post) == want, 'READBACK MISMATCH')
    print('SUCCESS: recovery =', img.name, 'readback verified. boot untouched.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('STOPPED:', repr(e), flush=True); sys.exit(1)
