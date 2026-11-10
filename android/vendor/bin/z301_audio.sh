#!/vendor/bin/busybox sh
# Z301ML audio: route AFE DL1 (card 0 device 0, used by the AIDL audio HAL) to the MT6328 DAC and
# the headphone output, which also feeds the external speaker amp (enable = GPIO9, "Ext Spk" DAPM
# widget in the machine driver). The MT6328 IV-buffer/class-D speaker path is not wired on this board.
# Modules are insmod-ed by init (on post-fs).
B=/vendor/bin/busybox; T=/vendor/bin/tinymix
log() { echo "z301_audio: $*" > /dev/kmsg; }

i=0; while [ ! -e /dev/snd/controlC0 ] && [ $i -lt 50 ]; do $B usleep 100000; i=$((i+1)); done
[ -e /dev/snd/controlC0 ] || { log "no sound card"; exit 1; }

set_ctl() { $T -D 0 set "$1" $2 >/dev/null 2>&1 || log "tinymix set '$1' failed"; }
set_ctl "ADDA_DL_CH1 DL1_CH1" 1
set_ctl "ADDA_DL_CH2 DL1_CH2" 1
set_ctl "Speaker Mode" Off
set_ctl "SPK Path Switch" 0
set_ctl "HP Path Switch" 1
set_ctl "Headphone Volume" "12 12"
log "speaker route set (HP output -> ext amp)"
