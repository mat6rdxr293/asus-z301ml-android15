# Android 15 on ASUS ZenPad 10 Z301ML (P00L, MT8735)

Port of an Android 15 GSI to the ASUS ZenPad 10 Z301ML (MediaTek MT8735 / MT6735, Mali-T720 MP2,
PMIC MT6328, CONNSYS MT6625L) on a mainline **Linux 7.0** kernel.

## Status

| Part | State |
|---|---|
| Display (LK handover, BOE NT35523 panel, LP8557 backlight) | works |
| Touch (FocalTech FT5x26 via edt-ft5x06) | works |
| GPU — Mali-T720 via Panfrost + Mesa 25.0.7 (GLES 2.0) | works (SurfaceFlinger + HWUI) |
| Wi-Fi (MTK wlan gen2, ported) | scan + connect work (PIO mode) |
| Bluetooth (WMT/STP + own HCI driver `btmtkstp`) | pairing works |
| Speaker (AFE + MT6328 codec + ext amp) | works |
| Power key, battery, cpufreq, thermal | work |
| Headphone detection, microphone, camera, sensors, modem | not done |

## Layout

- `kernel/` — patches against `v7.0.10-mt6735` of <https://gitlab.com/mt6735-mainline/linux>
  (`0001-*` = checkpoint commit, `0002-*` = later work) and kernel configs (`configs/`).
- `connsys/` — vendor MTK WMT / STP / BTIF / wlan gen2 drivers ported to Linux 7.0 (out-of-tree modules),
  incl. `wmt/linux/btmtkstp.c` (HCI driver for the CONNSYS Bluetooth core).
- `android/` — build/flash scripts, the vendor partition configuration (`vendor/`: init rc, build.prop,
  SELinux, VINTF, audio policy, helper scripts), source patches (`patches/`), connsys user-space tools.
- `gpu/` — Mesa cross-build for Android with the NDK (`build_mesa.sh`) and an EGL smoke test.
- `mainline/` — rescue-Linux / bring-up scripts (serial helper, catch-and-flash via mtkclient) and board patches.
- `docs/` — bring-up notes.

Binary blobs (stock firmware, GSI, Cuttlefish APEXes, CONNSYS firmware, built images) are not included.

## Build (short)

1. Kernel: check out the base tag, `git am kernel/0001-*.patch && git apply kernel/0002-*.patch`,
   config = allnoconfig + `configs/frag.config` + `configs/android.frag` (see `android/build_android_kernel.sh`).
2. Modules: panfrost / sound in-tree (`make modules`), connsys out-of-tree (`make M=connsys/...`).
3. Mesa: `gpu/build_mesa.sh` (needs Android NDK r27, meson, mako, bison ≥ 3).
4. Vendor image: `android/build_vendor.sh` (ext4, flashed to the 400 MB cache partition, mounted as /vendor).
5. Flash from rescue Linux: `android/android_try.sh <boot.img> [vendor.img]`.
