#!/vendor/bin/busybox sh
# Root debug console on USB ACM (/dev/ttyGS0). Runs from vendor init in permissive SELinux.
B=/vendor/bin/busybox
export PATH=/system/bin:/system/xbin:/vendor/bin:/vendor/bb
while true; do
  if [ -c /dev/ttyGS0 ]; then
    $B setsid $B sh -c "exec $B sh -i </dev/ttyGS0 >/dev/ttyGS0 2>&1"
  fi
  $B sleep 1
done
