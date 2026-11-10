#!/bin/bash
# build_android_kernel.sh TAG  -> mainline/artifacts/TAG-android-boot-FULL16MiB.img
set -e; T=$1; M=/Users/matveysazhnov/ASUS-Z301ML-port/mainline
limactl shell z301ml-kernel -- bash -lc "set -e; cd ~/z301ml-port/mainline/linux-mt6735-7.0; O=../build-android; cat ../build-tiny/frag.config ../android.frag > \$O/frag.config; make O=\$O ARCH=arm64 KCONFIG_ALLCONFIG=\$O/frag.config allnoconfig >/dev/null 2>&1; make O=\$O ARCH=arm64 -j4 Image mediatek/mt6735-asus-p00l-android.dtb 2>&1 | grep -iE ' error|Error [0-9]' || true; cd ..; zimage64/mkzimage64 build-android/arch/arm64/boot/Image probe/zimg-$T.bin --payload probe/fbprobe4.bin >/dev/null"
G=/home/matveysazhnov.guest/z301ml-port/mainline
cd $M; limactl copy z301ml-kernel:$G/probe/zimg-$T.bin artifacts/; limactl copy z301ml-kernel:$G/build-android/arch/arm64/boot/dts/mediatek/mt6735-asus-p00l-android.dtb artifacts/mt6735-asus-p00l-android-$T.dtb; limactl copy z301ml-kernel:$G/build-android/.config artifacts/linux-7.0.10-android-$T.config
python3 mkpadded.py artifacts/zimg-$T.bin artifacts/mt6735-asus-p00l-android-$T.dtb artifacts/$T-PADDED.bin
RAMDISK=../android/work/android-ramdisk.cpio.gz python3 pack_recovery.py artifacts/$T-PADDED.bin artifacts/$T-android-boot-FULL16MiB.img
