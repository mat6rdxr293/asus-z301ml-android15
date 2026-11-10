#!/bin/sh
# ASUS Z301ML / MT8735A mainline 7.0 diagnostic — no eMMC writes.
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
BB=/bin/busybox
$BB mkdir -p /dev /proc /sys /tmp /run /dev/pts /sys/kernel/config /sys/kernel/debug /sys/fs/pstore
$BB mount -t devtmpfs devtmpfs /dev 2>/dev/null || :
exec </dev/console >/dev/console 2>&1
$BB mount -t proc proc /proc 2>/dev/null || :
$BB mount -t sysfs sysfs /sys 2>/dev/null || :
$BB mount -t devpts devpts /dev/pts 2>/dev/null || :
$BB mount -t configfs configfs /sys/kernel/config 2>/dev/null || :
$BB mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || :
$BB mount -t pstore pstore /sys/fs/pstore 2>/dev/null || :
echo "===== Z301ML MAINLINE 7.0 INIT V2: EARLY BOOT SUCCESS ====="
$BB uname -a
echo "Kernel cmdline: $($BB cat /proc/cmdline)"
echo "Partitions (read-only listing):"
$BB cat /proc/partitions
echo "Framebuffer:"
$BB ls -l /dev/fb* 2>/dev/null || echo "No /dev/fb0 (needs bootloader simplefb handoff)"
echo "UDC enumeration:"
$BB ls /sys/class/udc 2>/dev/null || :
$BB dmesg | $BB tail -n 60

G=/sys/kernel/config/usb_gadget/p00l_diag
if [ -d /sys/kernel/config/usb_gadget ]; then
  $BB mkdir -p "$G" "$G/strings/0x409" "$G/configs/c.1/strings/0x409" "$G/configs/c.2/strings/0x409"
  echo 0x1d6b > "$G/idVendor" 2>/dev/null || :
  echo 0x0104 > "$G/idProduct" 2>/dev/null || :
  echo 0x0200 > "$G/bcdUSB" 2>/dev/null || :
  echo "P00L-LINUX7-TEST" > "$G/strings/0x409/serialnumber" 2>/dev/null || :
  echo "ASUS P00L kernel diagnostic" > "$G/strings/0x409/manufacturer" 2>/dev/null || :
  echo "Z301ML ACM ECM RNDIS" > "$G/strings/0x409/product" 2>/dev/null || :
  echo "Mac Linux ACM+ECM" > "$G/configs/c.1/strings/0x409/configuration" 2>/dev/null || :
  echo "Windows Linux ACM+RNDIS" > "$G/configs/c.2/strings/0x409/configuration" 2>/dev/null || :
  echo 100 > "$G/configs/c.1/MaxPower" 2>/dev/null || :
  echo 100 > "$G/configs/c.2/MaxPower" 2>/dev/null || :
  if $BB mkdir -p "$G/functions/acm.usb0"; then
    $BB ln -s "$G/functions/acm.usb0" "$G/configs/c.1/acm.usb0" 2>/dev/null || :
  else
    echo "Failed creating ACM function"
  fi
  if $BB mkdir -p "$G/functions/acm.usb1"; then
    $BB ln -s "$G/functions/acm.usb1" "$G/configs/c.2/acm.usb1" 2>/dev/null || :
  fi
  if $BB mkdir -p "$G/functions/ecm.usb0"; then
    echo "02:00:00:00:aa:01" > "$G/functions/ecm.usb0/dev_addr" 2>/dev/null || :
    echo "02:00:00:00:aa:02" > "$G/functions/ecm.usb0/host_addr" 2>/dev/null || :
    $BB ln -s "$G/functions/ecm.usb0" "$G/configs/c.1/ecm.usb0" 2>/dev/null || :
  fi
  if $BB mkdir -p "$G/functions/rndis.usb0"; then
    echo "02:00:00:00:bb:01" > "$G/functions/rndis.usb0/dev_addr" 2>/dev/null || :
    echo "02:00:00:00:bb:02" > "$G/functions/rndis.usb0/host_addr" 2>/dev/null || :
    $BB ln -s "$G/functions/rndis.usb0" "$G/configs/c.2/rndis.usb0" 2>/dev/null || :
  fi
  UDC=""
  for u in /sys/class/udc/*; do
    if [ -e "$u" ]; then UDC=$($BB basename "$u"); break; fi
  done
  if [ -n "$UDC" ]; then
    echo "Binding ConfigFS USB gadget to $UDC"
    if echo "$UDC" > "$G/UDC"; then
      echo "USB gadget bound"
      $BB ifconfig usb0 192.168.77.2 netmask 255.255.255.0 up 2>/dev/null || :
      $BB ifconfig usb1 192.168.77.2 netmask 255.255.255.0 up 2>/dev/null || :
    else
      echo "Gadget UDC bind failed"
    fi
  else
    echo "NO UDC: check MT6735 MUSB/PHY VBUS wiring"
  fi
else
  echo "NO CONFIGFS gadget interface"
fi

echo "Post-USB gadget status:"
$BB ls -l /dev/ttyGS* 2>/dev/null || :
$BB dmesg | $BB tail -n 80
echo "All eMMC partitions remain untouched."
(
  for t in 1 2 3 4 5 6 7 8 9 10; do
    if [ -c /dev/ttyGS0 ]; then
      echo "Z301ML mainline early diagnostic shell" >/dev/ttyGS0 2>/dev/null || :
      exec </dev/ttyGS0 >/dev/ttyGS0 2>&1
      exec /bin/busybox sh -i
    fi
    $BB sleep 1
  done
) &
exec /bin/busybox sh -i
