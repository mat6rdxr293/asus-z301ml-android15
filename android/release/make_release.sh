#!/bin/bash
# make_release.sh KERNELTAG VERSION
#   -> android/release/out/Z301ML-Android15-VERSION/{boot.img,vendor.img,system.img,flash/,README*}
# Turns the bring-up vendor tree into a release one (no auto-reboot/debug logging, no USB root console,
# secure adb), packs boot with the release pre-init ramdisk, copies the GSI and the flasher scripts.
set -e
TAG=${1:?kernel tag, e.g. A41}; VER=${2:?version, e.g. 0.1}
R=/Users/matveysazhnov/ASUS-Z301ML-port; A=$R/android; REL=$A/release
OUT=$REL/out/Z301ML-Android15-$VER; W=$REL/work
rm -rf "$W" "$OUT"; mkdir -p "$W" "$OUT"

# ---- release vendor tree
rsync -a --exclude '._*' --exclude '.DS_Store' "$A/work/vendor/" "$W/vendor/"
V=$W/vendor; RC=$V/etc/init/hw/init.mt6735.rc
python3 - "$V" <<'EOF'
import sys, re
V = sys.argv[1]
def edit(path, pairs):
    s = open(path).read()
    for old, new in pairs:
        assert old in s, (path, old)
        s = s.replace(old, new)
    open(path, 'w').write(s)
rc = V + '/etc/init/hw/init.mt6735.rc'
edit(rc, [
    ("    start vdmesg\n    start vlogcat\n    start autoreboot\n    start vdiag\n", ""),
    ("on property:sys.boot_completed=1\n    start z301_gpudiag\n", ""),
    ('write /proc/sys/kernel/printk "7 4 1 7"', 'write /proc/sys/kernel/printk "4 4 1 7"'),
    ("    write /sys/power/wake_lock z301ml_bringup\n", ""),
])
edit(V + '/etc/init/hw/init.mt6735.usb.rc', [("    start rootcon\n", "")])
edit(V + '/build.prop', [
    ("ro.secure=0\n", "ro.secure=1\n"),
    ("ro.adb.secure=0\n", "ro.adb.secure=1\n"),
    ("ro.debuggable=1\n", "ro.debuggable=0\n"),
    ("ro.vendor.build.type=userdebug\n", "ro.vendor.build.type=user\n"),
])
EOF
rm -f "$V/bin/diag.sh" "$V/bin/rootcon.sh"

COPYFILE_DISABLE=1 tar czf "$W/vendor.tgz" --no-xattrs -C "$V" .
limactl copy "$W/vendor.tgz" z301ml-kernel:/tmp/vendor-rel.tgz
limactl shell z301ml-kernel -- bash -c 'set -e; sudo rm -rf /tmp/vrel /tmp/vendor-rel.img; sudo mkdir /tmp/vrel; sudo tar xzf /tmp/vendor-rel.tgz -C /tmp/vrel 2>/dev/null; sudo chown -R root:root /tmp/vrel; sudo find /tmp/vrel -type d -exec chmod 755 {} +; sudo find /tmp/vrel -type f -exec chmod 644 {} +; sudo chmod 755 /tmp/vrel/bin/*; [ -d /tmp/vrel/bin/hw ] && sudo chmod 755 /tmp/vrel/bin/hw/*; sudo mkfs.ext4 -q -L vendor -O ^metadata_csum,^64bit -b 4096 -d /tmp/vrel /tmp/vendor-rel.img 192M; sudo chown $(id -u) /tmp/vendor-rel.img'
limactl copy z301ml-kernel:/tmp/vendor-rel.img "$OUT/vendor.img"

# ---- release boot image (same kernel+DTB as the bring-up TAG, release pre-init ramdisk)
mkdir -p "$W/rd/bin" "$W/rd/dev" "$W/rd/proc" "$W/rd/sys" "$W/rd/newroot"
cp "$A/work/ard/bin/busybox" "$W/rd/bin/busybox"; cp "$REL/ard-user-init" "$W/rd/init"; chmod 755 "$W/rd/init" "$W/rd/bin/busybox"
(cd "$W/rd" && find . | cpio -o -H newc -R 0:0 2>/dev/null | gzip -9 > "$W/ramdisk.cpio.gz")
(cd "$R/mainline" && RAMDISK="$W/ramdisk.cpio.gz" python3 pack_recovery.py "artifacts/$TAG-PADDED.bin" "$OUT/boot.img" >/dev/null)

# ---- GSI system + flasher + docs
cp "$A/gsi/system.img" "$OUT/system.img"
cp -R "$REL/flash" "$OUT/flash"
cp "$REL/README.md" "$OUT/README.md"
(cd "$OUT" && shasum -a 256 boot.img vendor.img system.img > SHA256SUMS)
ls -la "$OUT"; cat "$OUT/SHA256SUMS"
