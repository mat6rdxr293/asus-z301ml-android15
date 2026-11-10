#!/vendor/bin/busybox sh
# Z301ML connectivity bring-up (MT6735 CONSYS: BTIF/WMT/STP + launcher), then:
#   Bluetooth: hci0 via btmtkstp for the btlinux HAL     (skip with /data/vendor/no_bt)
#   Wi-Fi:     wlan0 via MTK wlan gen2 + wmt_chrdev_wifi  (skip with /data/vendor/no_wifi)
# Factory data is read from the ASUS persist (BD_ADDR, Wi-Fi MAC) and nvdata (Wi-Fi NVRAM
# calibration) partitions, mounted read-only under /data/vendor for the drivers.
B=/vendor/bin/busybox; M=/vendor/lib/modules
log() { echo "z301_conn: $*" > /dev/kmsg; }

$B mkdir -p /data/vendor/log
P=/data/vendor/persist_ro; N=/data/vendor/nvdata_ro
$B mkdir -p $P $N
$B grep -q " $P " /proc/mounts || $B mount -t ext4 -o ro,noload /dev/block/by-name/persist $P || log "persist mount failed"
$B grep -q " $N " /proc/mounts || $B mount -t ext4 -o ro,noload /dev/block/by-name/nvdata $N || log "nvdata mount failed"

for m in rfkill btif mtk_wmt; do $B insmod $M/$m.ko || log "insmod $m failed"; done
i=0; while [ ! -e /dev/stpwmt ] && [ $i -lt 50 ]; do $B usleep 100000; i=$((i+1)); done
export Z301_FWDIR=/vendor/firmware
/vendor/bin/z301-wmt-launcher > /data/vendor/log/wmt-launcher.txt 2>&1 &
L=$!
$B sleep 3

if [ -e /data/vendor/no_bt ]; then
	log "Bluetooth disabled by /data/vendor/no_bt"
else
	for m in ecc ecdh_generic bluetooth; do $B insmod $M/$m.ko || log "insmod $m failed"; done
	A=$($B head -c 17 $P/bt/bd_addr.conf 2>/dev/null)
	echo "$A" | $B grep -qE '^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$' || { log "no factory BD_ADDR ($A)"; A=; }
	$B insmod $M/btmtkstp.ko ${A:+bdaddr=$A} || log "insmod btmtkstp failed"
fi

if [ -e /data/vendor/no_wifi ]; then
	log "Wi-Fi disabled by /data/vendor/no_wifi"
else
	for m in cfg80211 wmt_chrdev_wifi wlan_gen2; do $B insmod $M/$m.ko || log "insmod $m failed"; done
	i=0; while [ ! -e /dev/wmtWifi ] && [ $i -lt 50 ]; do $B usleep 100000; i=$((i+1)); done
	# power the Wi-Fi function on: WMT func on + firmware download, then wlan0 registers
	echo 1 > /dev/wmtWifi || log "wmtWifi power-on failed"
	i=0; while [ ! -e /sys/class/net/wlan0 ] && [ $i -lt 100 ]; do $B usleep 100000; i=$((i+1)); done
	[ -e /sys/class/net/wlan0 ] && log "wlan0 up" || log "wlan0 did not appear"
fi

log "connectivity modules loaded, launcher pid $L"
wait $L
log "launcher exited $?"
