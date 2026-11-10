#!/vendor/bin/busybox sh
# called when adbd's FunctionFS is ready: build config b.1 = f1 adb + f9 ACM console, (re)bind UDC.
# Must be idempotent: unbinding a bound gadget here makes adbd see FUNCTIONFS_UNBIND, reopen
# FunctionFS and toggle sys.usb.ffs.ready again -> endless rebind loop (USB vanishes on the host).
B=/vendor/bin/busybox; G=/config/usb_gadget/g1; U=musb-hdrc.4.auto
if [ -L $G/configs/b.1/f1 ]; then
	# adb already in the config; when adbd restarts the kernel unbinds the gadget itself
	[ -n "$(cat $G/UDC 2>/dev/null)" ] || echo $U > $G/UDC
	exit 0
fi
echo > $G/UDC 2>/dev/null
$B ln -sf $G/functions/ffs.adb $G/configs/b.1/f1
$B ln -sf $G/functions/acm.gs0 $G/configs/b.1/f9
$B sleep 0.2
echo $U > $G/UDC
