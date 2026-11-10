#!/vendor/bin/busybox sh
# add ECM network (f8) to gadget g1, address usb0 169.254.77.2/16 (same as rescue Linux); adb also over TCP 5555
B=/vendor/bin/busybox; G=/config/usb_gadget/g1
[ -d $G/functions/ecm.usb0 ] || $B mkdir $G/functions/ecm.usb0
echo 02:00:00:00:aa:01 > $G/functions/ecm.usb0/dev_addr 2>/dev/null
echo 02:00:00:00:aa:02 > $G/functions/ecm.usb0/host_addr 2>/dev/null
echo > $G/UDC 2>/dev/null
$B ln -sf $G/functions/ecm.usb0 $G/configs/b.1/f8
$B sleep 0.2
echo musb-hdrc.4.auto > $G/UDC
$B sleep 1
$B ip link set usb0 up; $B ip addr add 169.254.77.2/16 dev usb0 2>/dev/null
