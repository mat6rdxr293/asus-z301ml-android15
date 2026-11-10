#!/usr/bin/env python3
"""
Android 15 installer for ASUS ZenPad 10 Z301ML (P00L, MT8735) using mtkclient (BROM mode).

  python z301ml_flash.py --mtk /path/to/mtkclient/mtk.py backup   # step 1: read-only, full backup + checks
  python z301ml_flash.py --mtk /path/to/mtkclient/mtk.py install  # step 2: write Android 15
  python z301ml_flash.py --mtk /path/to/mtkclient/mtk.py restore  # back to stock from your backup

Entering BROM: tablet OFF, unplug USB, hold Volume DOWN, plug USB in, release when mtkclient connects.
Every step needs a fresh BROM entry (unplug, hold Vol-, replug).
"""
import argparse, hashlib, os, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
BACKUP = os.path.join(PKG, "backup")

# GPT of the Z301ML (P00L) eMMC (HBG4a2 29.1 GiB): name -> (first LBA, sectors), 512-byte sectors.
# The installer refuses to write anything if the device does not match.
EXPECTED = {
    "persist": (1024, 98304), "proinfo": (99328, 6144), "nvram": (105472, 10240),
    "lk": (156672, 1024), "para": (157696, 1024), "boot": (158720, 32768),
    "recovery": (191488, 32768), "nvdata": (317440, 65536), "asusfw": (1030144, 344064),
    "system": (1392640, 7864320), "cache": (9256960, 819200), "userdata": (10076160, 50961408),
}
# partitions the installer overwrites (stock copies needed for restore)
TOUCHED = ["boot", "system", "cache", "para"]
# never written by this tool; backed up because losing them = no IMEI/Wi-Fi/BT calibration
PRECIOUS = ["nvram", "nvdata", "persist", "proinfo", "protect1", "protect2"]
IMAGES = {"boot": "boot.img", "system": "system.img", "cache": "vendor.img"}


def die(msg):
    print("\nERROR: " + msg)
    sys.exit(1)


def ask(msg):
    print(msg)
    if input("Type YES to continue: ").strip() != "YES":
        die("aborted by user")


def run_mtk(mtk, args):
    cmd = [sys.executable, mtk] + args
    print("\n>>> " + " ".join(cmd))
    print("    Now: tablet off, unplug USB, hold VOLUME DOWN, plug USB in (release when it connects).\n")
    r = subprocess.run(cmd, cwd=PKG)
    if r.returncode != 0:
        die("mtkclient failed (exit %d)" % r.returncode)


def parse_gpt(path):
    data = open(path, "rb").read()
    hdr = data.find(b"EFI PART")
    if hdr < 0:
        die("no GPT header in " + path)
    base = hdr - 512                       # header is LBA1
    ent_lba, n, esz = struct.unpack_from("<QII", data, hdr + 72)
    parts = {}
    for i in range(n):
        off = base + ent_lba * 512 + i * esz
        if off + esz > len(data):
            break
        e = data[off:off + esz]
        if e[:16] == bytes(16):
            continue
        first, last = struct.unpack_from("<QQ", e, 32)
        name = e[56:128].decode("utf-16-le").split("\0")[0]
        parts[name] = (first, last - first + 1)
    return parts


def check_gpt(path):
    parts = parse_gpt(path)
    bad = [f"{k}: expected {v}, device {parts.get(k)}" for k, v in EXPECTED.items() if parts.get(k) != v]
    if bad:
        die("this is not a Z301ML (P00L) with the expected partition layout:\n  " + "\n  ".join(bad))
    print("GPT OK: partition layout matches Z301ML (P00L)")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check_package():
    sums = {}
    for line in open(os.path.join(PKG, "SHA256SUMS")):
        h, name = line.split()
        sums[name] = h
    for name in IMAGES.values():
        p = os.path.join(PKG, name)
        if not os.path.isfile(p):
            die("missing " + name)
        print("checking " + name + " ...")
        if sha256(p) != sums[name]:
            die(name + " is corrupted (SHA256 mismatch), download again")


def check_backup():
    gpt = os.path.join(BACKUP, "gpt.bin")
    if not os.path.isfile(gpt):
        die("no backup found - run the 'backup' step first")
    check_gpt(gpt)
    for p in TOUCHED + PRECIOUS:
        f = os.path.join(BACKUP, p + ".bin")
        size = EXPECTED.get(p, (0, 0))[1] * 512
        if not os.path.isfile(f) or os.path.getsize(f) == 0 or (size and os.path.getsize(f) != size):
            die("backup of '%s' is missing or incomplete (%s)" % (p, f))
    print("backup OK: " + BACKUP)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mtk", required=True, help="path to mtkclient's mtk.py")
    ap.add_argument("step", choices=["backup", "install", "restore"])
    a = ap.parse_args()
    mtk = os.path.abspath(a.mtk)
    if not os.path.isfile(mtk):
        die("mtk.py not found: " + mtk)

    if a.step == "backup":
        if os.path.exists(os.path.join(BACKUP, "gpt.bin")):
            die("backup/ already exists - move it away first, never overwrite your only backup")
        print("Reading ALL partitions except userdata into backup/ (several GB, can take 30-60 min).")
        run_mtk(mtk, ["rl", "backup", "--skip", "userdata"])
        check_backup()
        print("\nDone. Copy the backup/ folder somewhere safe - it contains your IMEI, Wi-Fi/BT MACs and")
        print("calibration (nvram, nvdata, persist). Do not share it. Then run the 'install' step.")

    elif a.step == "install":
        check_package()
        check_backup()
        ask("\nThis ERASES the tablet: stock Android is replaced by Android 15, all user data is wiped.")
        run_mtk(mtk, ["multi",
                      "w boot,system,cache boot.img,system.img,vendor.img;"
                      "es para 1;es userdata 65536;reset"])
        print("\nDone. First boot takes 2-4 minutes (userdata gets formatted). Unplug USB if it stays black.")

    elif a.step == "restore":
        check_backup()
        ask("\nThis writes your stock boot/system/cache/para back and wipes userdata.")
        files = ",".join("backup/%s.bin" % p for p in TOUCHED)
        run_mtk(mtk, ["multi", "w %s %s;es userdata 65536;reset" % (",".join(TOUCHED), files)])
        print("\nDone. Stock Android should boot (first boot is slow).")


if __name__ == "__main__":
    main()
