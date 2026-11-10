#!/bin/bash
# android_try.sh BOOTIMG [VENDORIMG]  (tablet must be in rescue Linux; Mac http server on :8765 at repo root)
# flash boot (+vendor) from rescue Linux, verify, clear BCB, reboot, wait for result, save pstore log.
set -e; R=/Users/matveysazhnov/ASUS-Z301ML-port; cd $R/mainline
PY=/Users/matveysazhnov/mtkclient/.venv/bin/python
IF=$(networksetup -listallhardwareports | awk '/Hardware Port: Z301ML/{getline; print $2; exit}')
for i in $(seq 1 30); do MIP=$(ipconfig getifaddr $IF || true); [ -n "$MIP" ] && break; sleep 2; done; echo "mac $IF $MIP"; [ -n "$MIP" ] || { echo "NO MAC IP"; exit 1; }
pkill -f "http.server 8765" || true; (cd $R && python3 -m http.server 8765 --bind $MIP >/tmp/http.log 2>&1 &); sleep 1
BI=$1; VI=$2; BS=$(shasum -a 256 $R/$BI | cut -c1-64); VS=""; [ -n "$VI" ] && VS=$(shasum -a 256 $R/$VI | cut -c1-64)
FP='fp(){ for u in /sys/class/block/*/uevent; do grep -q "^PARTNAME=$1$" $u && basename $(dirname $u); done; }'
$PY ttyq.py "$FP; ip addr add 169.254.77.2/16 dev usb0 2>/dev/null; ip link set usb0 up; B=\$(fp boot); wget -q -O - http://$MIP:8765/$BI | dd of=/dev/\$B bs=1M 2>/dev/null; sync; sha256sum /dev/\$B" 120 | grep -q "$BS" || { echo "BOOT VERIFY FAIL"; exit 1; }
echo "boot ok $BS"
if [ -n "$VI" ]; then
  SZ=$(stat -f %z $R/$VI)
  $PY ttyq.py "$FP; C=\$(fp cache); wget -q -O - http://$MIP:8765/$VI | dd of=/dev/\$C bs=1M 2>/dev/null; sync; head -c $SZ /dev/\$C | sha256sum" 200 | grep -q "$VS" || { echo "VENDOR VERIFY FAIL"; exit 1; }
  echo "vendor ok $VS"
fi
$PY ttyq.py "$FP; P=\$(fp para); head -c 32 /dev/zero | dd of=/dev/\$P bs=32 count=1 conv=notrunc,fsync 2>/dev/null; sync; sh -c 'sleep 2; reboot -f' >/dev/null 2>&1 & true" 15 >/dev/null
echo "rebooted $(date +%T)"; sleep 20
for i in $(seq 1 40); do
  if ls /dev/cu.usbmodem[0-9]* >/dev/null 2>&1; then
    O=$($PY ttyq.py '[ -e /system/bin/getprop ] && echo OS=ANDROID || echo OS=LINUX' 8 2>/dev/null | grep -ao "OS=[A-Z]*" | tail -1)
    [ -n "$O" ] && { echo "$O $(date +%T)"; break; }
  fi
  adb devices | grep -q "^P00L-LINUX7-TEST.*device$" && { echo "OS=ANDROID(adb) $(date +%T)"; break; }
  sleep 4
done
[ "$O" = OS=LINUX ] && $PY ttyq.py 'cat /sys/fs/pstore/console-ramoops-0' 60 > /tmp/android-last.log && wc -l /tmp/android-last.log
exit 0
