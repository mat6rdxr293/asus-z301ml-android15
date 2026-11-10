#!/usr/bin/env python3
"""Guarded: set para ENV off-mode-charge=1 -> 0 (MTK LK ENV_v1 at para+0x20000).
With off-mode-charge=0 LK skips KPOC (power-off charging) when powered by USB,
so the tablet boots from cable insertion without the (broken) Power key.

Writes ONLY two 512-byte sectors of para: +0x20000 (value byte) and +0x23e00
(ENV checksum at +0x23ffc = sum of env data bytes). Full 512 KiB pre-read must
equal the known post-BCB para; full readback must equal expected; else restore.
Run: sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u THIS [--check]
"""
import os, sys, logging, hashlib, struct, json, subprocess
from pathlib import Path

H = Path('/Users/matveysazhnov')
MTK = H / 'mtkclient'
W = H / 'ASUS-Z301ML-port/mainline/recovery-readcheck'
KNOWN = W / 'para-after-boot-recovery-guard.bin'
KNOWN_SHA = '5b621a57fcd12644e542f2aab563e2b00289ff4bd38c0bed0ba6236c47a28680'
BEFORE = W / 'para-before-offmode0.bin'
AFTER = W / 'para-after-offmode0.bin'
EXPECT = W / 'para-expected-offmode0.bin'
SEC_DIR = W / 'offmode0-sectors'
MEID = 'e38fd44f882d91c96dfa77e29b2cc032'
PARA_ADDR, PARA_LEN = 0x04d00000, 0x80000
ENV = 0x20000
TAIL = 0x23ff4
CKSUM = 0x23ffc
KEY = b'off-mode-charge='


def ck(v, msg):
    if not v:
        raise RuntimeError('SAFETY STOP: ' + msg)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def build():
    d = bytearray(KNOWN.read_bytes())
    ck(len(d) == PARA_LEN and sha(d) == KNOWN_SHA, 'known para file mismatch')
    ck(d[ENV:ENV + 6] == b'ENV_v1' and d[TAIL:TAIL + 6] == b'ENV_v1', 'ENV signatures missing')
    old = struct.unpack('<I', d[CKSUM:CKSUM + 4])[0]
    ck(old == sum(d[ENV + 8:TAIL]), 'stored ENV checksum != computed (format assumption wrong)')
    i = d.find(KEY, ENV, TAIL)
    ck(i > 0 and d[i + len(KEY)] == ord('1') and d[i + len(KEY) + 1] == 0, 'off-mode-charge=1 not found')
    d[i + len(KEY)] = ord('0')
    new = sum(d[ENV + 8:TAIL])
    ck(new == old - 1, 'checksum delta unexpected')
    d[CKSUM:CKSUM + 4] = struct.pack('<I', new)
    diff = [k for k in range(PARA_LEN) if d[k] != KNOWN.read_bytes()[k]] if False else None
    orig = KNOWN.read_bytes()
    changed_secs = sorted({k // 512 * 512 for k in range(PARA_LEN) if d[k] != orig[k]})
    ck(changed_secs == [0x20000, 0x23e00], f'unexpected changed sectors {[hex(x) for x in changed_secs]}')
    print(f'PLAN: value byte @para+{i + len(KEY):#x} 1->0, checksum {old:#x}->{new:#x}; sectors {[hex(x) for x in changed_secs]}', flush=True)
    return bytes(d), changed_secs


def main():
    expected, secs = build()
    s = json.loads((MTK / '.state').read_text())
    ck(s.get('hwcode') == 0x321 and s.get('flashmode') == 'LEGACY' and s.get('patched') is True
       and s.get('meid') == MEID, 'mtkclient .state mismatch')
    u = subprocess.run(['ioreg', '-p', 'IOUSB', '-l', '-w0'], capture_output=True, text=True, timeout=7).stdout
    ck('"idVendor" = 3725' in u and '"idProduct" = 8193' in u, 'DA 0e8d:2001 not on USB')
    print('PRECHECK PASS', flush=True)
    if '--check' in sys.argv:
        print('DRY RUN: 0 bytes written', flush=True)
        return
    ck(os.geteuid() == 0, 'run via sudo -n full venv python path')
    for p in (BEFORE, AFTER):
        ck(not p.exists(), f'{p} exists; refusing to overwrite evidence')
    SEC_DIR.mkdir(exist_ok=True)
    EXPECT.write_bytes(expected)
    for a in secs:
        (SEC_DIR / f'new-{a:#x}.bin').write_bytes(expected[a:a + 512])
        (SEC_DIR / f'orig-{a:#x}.bin').write_bytes(KNOWN.read_bytes()[a:a + 512])

    sys.modules['mfusepy'] = None
    os.chdir(MTK); sys.path.insert(0, str(MTK))
    from mtkclient.config.mtk_config import MtkConfig
    from mtkclient.Library.mtk_class import Mtk
    from mtkclient.Library.DA.mtk_da_handler import DaHandler
    from mtkclient.Library.Partitions.gpt import GptSettings
    cfg = MtkConfig(loglevel=logging.INFO); cfg.gpt_settings = GptSettings(0, 0, 0)
    mtk = Mtk(config=cfg, loglevel=logging.INFO)
    da = DaHandler(mtk, logging.INFO)
    print('Reusing existing patched legacy DA (no BROM handshake)...', flush=True)
    mtk = da.connect(mtk, directory='.')
    ck(mtk is not None and mtk.reinited, 'DA resume failed')
    mtk = da.configure_da(mtk)
    ck(mtk is not None and mtk.daloader.patch and mtk.config.hwcode == 0x321, 'wrong DA/CPU')
    found, part = mtk.daloader.detect_partition('para', parttype='user')
    ck(found and part.sector * 512 == PARA_ADDR and part.sectors * 512 == PARA_LEN, 'GPT para mismatch')
    ck(mtk.daloader.readflash(addr=PARA_ADDR, length=PARA_LEN, filename=str(BEFORE), parttype='user'), 'pre-read failed')
    ck(sha(BEFORE.read_bytes()) == KNOWN_SHA, 'LIVE para differs from known state; refuse write')
    print('PASS: live para == known (boot-recovery BCB, off-mode-charge=1)', flush=True)

    def restore():
        print('RESTORING original sectors', flush=True)
        for a in secs:
            mtk.daloader.writeflash(addr=PARA_ADDR + a, length=512, filename=str(SEC_DIR / f'orig-{a:#x}.bin'), parttype='user')
        r = W / 'para-restored-offmode0.bin'
        mtk.daloader.readflash(addr=PARA_ADDR, length=PARA_LEN, filename=str(r), parttype='user')
        print('restore SHA ok:', sha(r.read_bytes()) == KNOWN_SHA, flush=True)

    try:
        for a in secs:
            print(f'WRITE 512 B at para+{a:#x}', flush=True)
            ck(mtk.daloader.writeflash(addr=PARA_ADDR + a, length=512, filename=str(SEC_DIR / f'new-{a:#x}.bin'), parttype='user'), f'write {a:#x} failed')
        ck(mtk.daloader.readflash(addr=PARA_ADDR, length=PARA_LEN, filename=str(AFTER), parttype='user'), 'post-read failed')
        ck(AFTER.read_bytes() == expected, 'readback != expected')
    except BaseException:
        restore()
        raise
    print('SUCCESS: off-mode-charge=0, checksum updated, full 512 KiB readback verified', flush=True)
    print('AFTER SHA256', sha(expected), flush=True)
    print('Still in DA, not rebooted. boot/lk/recovery untouched.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('STOPPED:', repr(e), flush=True)
        sys.exit(1)
