#!/bin/bash
# connsys_test.sh TAG : pack oneshot image with current btif/mtk_wmt(/wlan) modules, reboot->rescue->boot it, load + run launcher
set -e; R=/Users/matveysazhnov/ASUS-Z301ML-port; W=$R/android/work; T=$1; PY=/Users/matveysazhnov/mtkclient/.venv/bin/python
G=/home/matveysazhnov.guest/z301ml-port/connsys
limactl copy z301ml-kernel:$G/btif/common/btif.ko $W/rd5/lib/modules/
limactl copy z301ml-kernel:$G/wmt/mtk_wmt.ko $W/rd5/lib/modules/
limactl copy z301ml-kernel:$G/wlan/wlan_drv_gen2.ko $W/rd5/lib/modules/ 2>/dev/null || true
(cd $W/rd5 && find . | cpio -o -H newc --owner 0:0 2>/dev/null | gzip -9 > $W/initramfs-oneshot-$T.cpio.gz)
cd $R/mainline; RAMDISK=../android/work/initramfs-oneshot-$T.cpio.gz python3 pack_recovery.py artifacts/A18-PADDED.bin artifacts/$T-oneshot-FULL16MiB.img >/dev/null
os() { $PY ttyq.py '[ -e /system/bin/getprop ] && echo OS=AND""ROID || echo OS=LI""NUX; uname -v' 6 2>/dev/null | grep -aoE "^OS=[A-Z]*|#[0-9]+ SMP" | tr '\n' ' '; }
case "$(os)" in *"#1 SMP"*) ;; *) $PY -c "import glob,serial,time; s=serial.Serial(glob.glob('/dev/cu.usbmodem[0-9]*')[0],115200); s.write(b'sync; echo b > /proc/sysrq-trigger\n'); time.sleep(1)" 2>/dev/null || true; adb -s P00L-LINUX7-TEST shell reboot >/dev/null 2>&1 || true; sleep 25
  for i in $(seq 1 80); do ls /dev/cu.usbmodem[0-9]* >/dev/null 2>&1 && case "$(os)" in *LINUX*"#1 SMP"*) break;; esac; sleep 3; done;; esac
echo "rescue ok $(date +%T)"
cd $R/android && ./android_try.sh mainline/artifacts/$T-oneshot-FULL16MiB.img | grep -E "boot ok|OS=|FAIL"
cd $R/mainline; $PY ttyq.py "cd /lib/modules; insmod btif.ko; insmod mtk_wmt.ko; [ -e wlan_drv_gen2.ko ] && insmod wlan_drv_gen2.ko; sleep 2; (Z301_FWDIR=/vendor/firmware z301-wmt-launcher ${2:-wifi} > /tmp/launcher.log 2>&1 &); sleep ${3:-20}; cat /tmp/launcher.log; dmesg | grep -iE 'WMT|STP|BTIF|consys|patch|wlan|wifi|EMI|chip' | grep -vE 'PM: |device_add|fwnode|Linked|kset|bus:' | tail -${4:-60}" 120 | cut -c1-200
