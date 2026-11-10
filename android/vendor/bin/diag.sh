#!/vendor/bin/busybox sh
# bring-up diagnostics -> /data/vendor/log/diag-<t>.txt at 60 s, 180 s, 400 s after /data mount
B=/vendor/bin/busybox
for t in 20 30 45 180; do
  case $t in 20) $B sleep 20;; 30) $B sleep 8;; 45) $B sleep 12;; *) $B sleep 130;; esac
  O=/data/vendor/log/diag-$t.txt
  {
    echo "=== uptime"; $B cat /proc/uptime
    echo "=== ps"; /system/bin/ps -A -o PID,PPID,USER,S,WCHAN,NAME 2>&1
    echo "=== getprop"; /system/bin/getprop 2>&1
    echo "=== services"; /system/bin/service list 2>&1 | $B head -80
    echo "=== usb"; $B ls -l /config/usb_gadget/g1/configs/b.1/ 2>&1; $B cat /config/usb_gadget/g1/UDC 2>&1
    for f in /sys/class/udc/*/state /sys/class/udc/*/current_speed; do echo "$f: $($B cat $f 2>&1)"; done
    echo "=== keystore2 stack"; P=$($B pidof keystore2); [ -n "$P" ] && /system/bin/debuggerd -b $P 2>&1
    echo "=== vold stack"; P=$($B pidof vold); [ -n "$P" ] && /system/bin/debuggerd -b $P 2>&1 | $B head -120
    echo "=== init wchan"; $B cat /proc/1/wchan; echo; $B cat /proc/1/stack 2>&1
    echo "=== mounts"; $B cat /proc/mounts
    echo "=== power"; $B cat /sys/power/wake_lock /sys/power/state 2>&1
  } > $O 2>&1
  $B sync
done
