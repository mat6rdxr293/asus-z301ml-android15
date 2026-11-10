# GPU acceleration handoff for the ASUS ZenPad 10 Z301ML (P00L) port

As of 2026-11-10.

## Goal

The Android 15 GSI currently draws everything on the CPU: SwiftShader Vulkan plus ANGLE GLES. SystemUI takes about 2 s per touch event. The aim is to make the UI usable by moving rendering to the Mali-T720 MP2 GPU through Mesa Panfrost.

## Device and constraints

- SoC: MT8735/MT6735, 4× Cortex-A53 at 1.3 GHz (already at max). GPU: Mali-T720 MP2 (Midgard v4).
- Mesa Panfrost supports only **OpenGL ES 2.0** on T720. There is no Vulkan for Midgard.
- SurfaceFlinger RenderEngine falls back to GLES2, and HWUI's skiagl pipeline uses a GLES 2 context. Blur needs GLES3, so keep blur disabled. Force `debug.hwui.renderer=skiagl`, because Vulkan currently exists only through SwiftShader.

### Hardware facts

- Only Volume+ is broken. Power and Vol− work.
- BROM: hold Vol− and plug in USB.
- The tablet does not power on over USB after a full power-off. Unplug the cable, hold Power, then replug.

### Safety

- A Samsung phone is connected to the Mac as `/dev/cu.usbmodemRFCX…` and adb serial `RFCXB0Z1TJF`. **Never touch it.** Scripts only glob `/dev/cu.usbmodem[0-9]*`.
- Ignore the network TV at `10.111.92.119:5555` in adb.

### Working with the user

- The user writes in Russian, is often remote, and is tired of long waits. Give short, concrete steps.

## Build and flash workflow

- **Mac repo:** `~/ASUS-Z301ML-port`.
- **Lima VM:** `z301ml-kernel`. The VM home is `/home/matveysazhnov.guest`, and the Mac home is mounted read-only at `/Users/matveysazhnov`.
- **Kernel tree:** VM `~/z301ml-port/mainline/linux-mt6735-7.0`. The checkpoint branch is `z301-checkpoint-A26`, and there are newer uncommitted changes.
  - Config: allnoconfig + `build-tiny/frag.config` + `~/z301ml-port/mainline/android.frag`.
- **Build a kernel image:**

  ```bash
  cd ~/ASUS-Z301ML-port/android && ./build_android_kernel.sh A40
  ```

  This produces `mainline/artifacts/A40-android-boot-FULL16MiB.img`. The script does **not** stop on compile errors: check that the FULL sha changed.
- **Kernel size limit:** the gzip Image must stay below about 8,392,704 bytes. A39 is 8,179,703, so about 210 KB is left. Build anything big as a module.
- **Modules:**
  - In-tree: `make O=../build-android ARCH=arm64 -j4 modules` in the kernel dir. Panfrost, gpu-sched and drm_shmem_helper are already built there.
  - Out-of-tree: `make O=../build-android ARCH=arm64 M=<dir> modules`.
- **Vendor image:**
  - The tree is `android/work/vendor`. Build it with `android/build_vendor.sh`, which writes `android/work/vendor.img` (ext4, 128 MB, flashed to the cache partition, mounted as /vendor).
  - SELinux: `vendor/etc/selinux/vendor_sepolicy.cil`. Add a domain block per new HAL type and mark it permissive (the kernel is permissive anyway). Verify the policy compiles in the VM:

    ```bash
    cd /tmp/selt && secilc -m -M true -G -c 30 -o out -f /dev/null plat_sepolicy.cil 202404.cil /tmp/ppv.cil /tmp/vsp.cil
    ```

  - Init: `vendor/etc/init/hw/init.mt6735.rc`. Connectivity startup is `vendor/bin/z301_bt.sh`.
- **Flash:**
  1. Get the tablet into rescue Linux: run `adb -s P00L-LINUX7-TEST reboot` from Android. BCB is re-armed, so it lands in rescue, uname `#1 SMP`.
  2. Then run:

     ```bash
     cd ~/ASUS-Z301ML-port/android && ./android_try.sh mainline/artifacts/AXX-android-boot-FULL16MiB.img [android/work/vendor.img] < /dev/null; pkill -f "http.server 8765"
     ```

     Redirect stdin and kill the http server afterwards. Without that, the pipe hangs.
  3. Android adb serial: `P00L-LINUX7-TEST`. adbd runs as root, and there is no su.
  4. Keep Android up with `touch /data/vendor/keep`. Without it, an autoreboot fires after 7 min.
- **Serial helper:** `mainline/ttyq.py '<cmd>' <timeout>`, run with `/Users/matveysazhnov/mtkclient/.venv/bin/python`.
- **Bootloop recovery without the user:** mtkclient `w boot <img>` catches the looping preloader.
- **Do not `devmem` MM or display registers while the screen is off.** The clocks are gated, the bus hangs and the watchdog resets.

## UPDATE 2026-11-10 23:30: GPU WORKS

Tablet is in Android on kernel **A40** (= A39 + DT `touchscreen-inverted-x` on touchscreen@38: screen Y was mirrored; inversion is applied before the x/y swap) + vendor **`81e9851d…`** (192 MB image; previous ANGLE vendor kept as
`android/work/vendor-4726aa21-angle.img`).

- **Mesa 25.0.7** panfrost, built on the **Mac** with the existing NDK r27 (`~/Library/Android/sdk/ndk/27.2.12479018`):
  `gpu/build_mesa.sh` (cross file `gpu/android-aarch64.cross`, sources `gpu/src`, python venv `gpu/venv`,
  brew bison). Mesa ≥ 25.1 needs LLVM+libclc on the host (panfrost libpan CL kernels) → stay on 25.0.x.
  `-Dandroid-stub=true`, static libdrm 2.4.134, u_gralloc = fallback (works for minigbm linear RGBA).
- vendor: `lib64/egl/lib{EGL,GLESv1_CM,GLESv2}_mesa.so`, `lib64/libgallium_dri.so`, plus `lib64/libhardware.so`
  and `lib64/libz.so` copied from GSI /system (not in the sphal link list). Props: `ro.hardware.egl=mesa`,
  `drm.gpu.vendor_name=panfrost`, `ro.opengles.version=131072`, `debug.hwui.renderer=skiagl`,
  `debug.renderengine.backend=skiaglthreaded`, `ro.surface_flinger.supports_background_blur=0`.
  init: `on post-fs` insmod drm_shmem_helper/gpu-sched/panfrost from `/vendor/lib/modules`; chmod card1/renderD129.
- Result: RenderEngine `Mali-T720 (Panfrost) OpenGL ES 2.0 Mesa 25.0.7`; SystemUI/Launcher HWUI on Mesa
  (Pipeline=Skia (OpenGL)). boot_completed < 1 min. Launcher swipes: 50th pct 24 ms/frame, GPU 10 ms;
  now CPU-bound ("Slow UI thread"). Report written each boot to `/data/vendor/log/gpu.txt` (z301_gpudiag).
- **Fixed USB/adb vanishing:** `vendor/bin/usb_adb.sh` unbound UDC on every `sys.usb.ffs.ready=1` → adbd got
  FUNCTIONFS_UNBIND → reopened → loop (5000+ rebinds). Now idempotent.
- `build_vendor.sh` image grown 128M → 192M (cache partition is 400 MB).
- Gotchas: unmount anything you mounted from cache/userdata in rescue before `android_try.sh` (else VENDOR VERIFY FAIL);
  `android_try.sh ... | tail` hangs until the http.server is killed (it inherits stdout) — redirect to a file.
- Open: SELinux labels for the new libs (all `vendor_file`, kernel permissive); "wide gamut" HWUI warning;
  try `debug.hwui.renderer=skiagl` perf tuning / disable HWUI features; SwiftShader Vulkan APEX still installed.

## UPDATE 2026-11-10 ~23:55: Bluetooth pairing

- Pairing crashed the Android BT stack: after SSP user confirmation CONNSYS sends Command Complete for
  vendor opcode 0xfcbd that the host never sent → GD hci_layer LOG_FATAL. `btmtkstp.c` now tracks sent
  vendor opcodes and drops unsolicited CC/CS for OGF 0x3f; also clamps Read Remote Ext Features max_page
  (stack walked pages up to 40). Patch: `android/patches/btmtkstp_vendor_evt.py` (applied in VM,
  backup `btmtkstp.c.pre-vendorevt`). Phone (Galaxy S24) now pairs.
- Only GATT/HearingAid profiles ran → nothing to connect. vendor build.prop now enables classic
  profiles (a2dp.source, avrcp.target, hfp.ag, hid.host, opp, pan.nap/panu, pbap/map server).
- vendor image built `34903ac4…` (module + profiles), NOT yet flashed; tablet runs the new module and
  profiles live (setprop + rmmod/insmod).

## UPDATE 2026-11-11 ~00:15: black windows + YouTube crash fixed

- **Black app windows / settings**: minigbm allocates every window buffer as a mediatek-drm dumb buffer
  from CMA; with GPU HWUI ~230 buffers (186 MB) filled cma=256M → CREATE_DUMB ENOMEM → black windows.
  Kernel **A41** = A40 + `cma=512M` (android DTS cmdline-override). Flashed with vendor 34903ac4.
- **YouTube in WebView**: (1) `media.extractor` SIGSYS on memfd_create (no ashmem → sys.use_memfd) →
  `vendor/etc/seccomp_policy/mediaextractor.policy` adds memfd_create/ftruncate/fcntl (merged by
  mediaextractor). (2) Mesa SIGSEGV: panfrost_ptr_unmap tiled→linear conversion util_copy_rect wrote
  through a stale BO mapping (glTexSubImage2D from Chromium GPU thread) → `debug.mesa.pan.mesa.debug=linear`
  (Mesa reads PAN_MESA_DEBUG from that prop). Video plays now.
- Both were applied live on /vendor (remount rw works as root); vendor tree image `62385719…` = what is on
  the tablet now (not flashed as image, but content identical).
- Still open: BT stack abort "Waiting for LE_SET_SCAN_PARAMETERS(0x200b), got LE_SET_SCAN_ENABLE(0x200c)"
  (controller sends an extra CC for 0x200c) — needs similar filtering in btmtkstp.

## UPDATE 2026-11-11 ~00:30: Sound works (to ALSA), BT scan crash fixed

- **"Sound hangs" was a kernel panic**: NULL deref in `mtk_memif_set_rate_substream` on the first
  hw_params. In Linux 7.0 `COMP_DUMMY()` is an empty array, so in `mt6735-mt6328.c` probe
  `dai_link->codecs` of the FE links aliased `platforms` and the codec node overwrote the DL1 platform →
  AFE `mtk-afe-pcm` component missing on the FE runtime. Fix: only touch codecs/platforms when
  num_codecs/num_platforms > 0 (`android/patches/snd_machine_dummy_fix.py`, applied in VM tree;
  `snd_machine_debug.py` = optional rtd component dump).
- vendor: `lib/modules/{snd-soc-mtk-common,snd-soc-mt6735-afe,snd-soc-mt6328,mt6735-mt6328}.ko`
  insmod in `on post-fs`, then `exec /vendor/bin/z301_audio.sh` (static tinymix: ADDA_DL_CH1/2 ← DL1,
  Speaker Mode ClassD, SPK Path Switch on, Headphone Volume 12). Cuttlefish AIDL HAL plays to card0/dev0:
  ALSA Playback_1 State: start, AudioFlinger OUT_SPEAKER frames advancing. Audible output NOT yet confirmed.
- **BT**: `android/patches/btmtkstp_all_cmd_evt.py` — track all outstanding HCI opcodes (bitmap 64K),
  drop CC/CS the host is not waiting for (duplicate CC for LE_SET_SCAN_ENABLE crashed GD stack).
- All applied live on /vendor; vendor tree image rebuilt.

## UPDATE 2026-11-11 ~00:45: SPEAKER SOUND WORKS (confirmed by ear, YouTube via Android)

Root causes after the panic fix (all in VM kernel tree, scripts in `android/patches/`, apply in this order
on clean files: snd_machine_dummy_fix, snd_machine_spk_from_hp, snd_afe_conn_mt6735, snd_afe_i2s_dac,
snd_codec_newif_clk; snd_machine_debug / snd_codec_debug_ctls are debug-only, not applied):
1. **AFE interconnect** (the real silence): mt6735-dai-adda.c used the mt6797 layout (O03/O04 in
   AFE_CONN3/4). MT6735: O03 = AFE_CONN1 bit 16+Ixx, O04 = AFE_CONN2 bit Ixx (vendor
   mt_soc_afe_connection.c). DL3/PCM-capture → O03/O04 don't exist on MT6735 (virtual switches).
2. AFE "I2S DAC out" AFE_I2S_CON1 (rate<<8 | I2S fmt 1<<3, bit0 as DAPM supply) like vendor SetI2SDacOut.
3. MT6328 one-time init: AFE_PMIC_NEWIF_CFG2 (0x203c) bit15 "reverse PMIC clock", AUDDEC_ANA_CON0 0xe000.
4. **Speaker amp input = codec headphone output (HPL/HPR)**, not the IV buffer/class-D (verified with
   pitch-coded tones). Machine route "Ext Spk" ← HPL only; z301_audio.sh: HP Path on, SPK Path off,
   Speaker Mode Off, Headphone Volume 12/18. White noise heard before = ext amp hiss with no signal.
- Live debug trick: `/vendor/bin/busybox devmem 0x112200xx` on AFE regs is safe only while a stream runs.
- vendor image rebuilt (see sha in build output); content == what is on the tablet.
- TODO: headphone jack detection (accdet) to mute the speaker amp; microphone/capture untested;
  set sane default volume curve.

## Previous state (before GPU)

The tablet was in Android on kernel **A39** with vendor `4726aa21…`.

### Working

- **Display:** LK handover. The panel is not re-initialised at boot.
- **Power key:** sleeps and wakes the screen.
- **Backlight:** LP8557 on i2c bus 1, address 0x2c. The panel driver switches it on and off.
- **Touch:** edt-ft5x06 delivers events fine. The UI is just slow.
- **Bluetooth:** factory BD_ADDR.
- **Wi-Fi:** wlan0 with the factory MAC. Scanning and connecting work (5 GHz WPA2, internet OK, 2026-11-10). The driver runs in PIO mode.

### GPU: done in A39

- **DT, in VM `arch/arm64/boot/dts/mediatek/mt6735-asus-p00l-android.dts`:**
  - `&gpu { status = "okay"; }`
  - `&mfgcfg { power-domains = <&spm MT6735_POWER_DOMAIN_MFG>; status = "okay"; }`
  - The gpu node itself is in `mt6735.dtsi`: compatible `mediatek,mt6735-mali`, `arm,mali-t720`, address 0x13040000, irqs 212/211/210, clock `CLK_MFG_BG3D`, MFG resets and power domain.
- **Driver:** `drivers/clk/mediatek/clk-mt6735-mfgcfg.c` now sets `.need_runtime_pm = true`.
- **`android.frag`:** adds `CONFIG_DRM_PANFROST=m` and `CONFIG_COMMON_CLK_MT6735_MFGCFG=y`. PM_DEVFREQ and IOMMU_IO_PGTABLE_LPAE get pulled in.
- **Verified by loading the modules by hand** (`insmod drm_shmem_helper.ko gpu-sched.ko panfrost.ko` from `/data/local/tmp`). They are **not in vendor yet**.

  ```
  panfrost 13040000.gpu: clock rate = 449999634
  mali-t720 id 0x720 major 0x1 minor 0x0 status 0x0
  shader_present=0x3 l2_present=0x1
  [drm] Initialized panfrost 1.6.0 ... minor 1
  ```

  - Device nodes: `/dev/dri/card1` and `/dev/dri/renderD129`. `card0` and `renderD128` are mediatek-drm, the display.
  - Warning: "no regulator (mali), using dummy". There is no OPP table, so there is no devfreq. That is fine.

### Current graphics stack in vendor (Cuttlefish parts)

- `com.android.hardware.graphics.composer.drm_hwcomposer` (HWC3 over `/dev/dri/card0`).
- `com.google.cf.gralloc`: minigbm gralloc on the render node. The kernel was patched with DRIVER_RENDER and DRM_RENDER_ALLOW on dumb ioctls so that minigbm can use the renderD node while hwc keeps DRM master.
- `com.google.cf.vulkan`: SwiftShader. GLES currently goes through ANGLE-on-SwiftShader from the GSI.
- `ro.hardware.*` / EGL props: check `vendor/build.prop` and the Cuttlefish APEX contents in the VM. The Cuttlefish vendor image is mounted at `/tmp/cfv`, and APEXes are unpacked with python zipfile plus a loop mount.

## Next steps

1. **Ask the user first.** Downloading needs explicit permission. That question was asked and not yet answered.
   - Android NDK r27, about 650 MB, from dl.google.com.
   - Mesa stable source, about 40 MB, from gitlab.freedesktop.org.
2. **Build Mesa for Android in the VM with the NDK.**
   - Options: `-Dplatforms=android -Dplatform-sdk-version=35 -Dgallium-drivers=panfrost -Dvulkan-drivers= -Degl=enabled -Dgles2=enabled -Dandroid-libbacktrace=disabled`, plus `-Dandroid-strict=false` or the equivalent.
   - Mesa's Android meson build needs the `cutils`, `hardware`, `sync` and `nativewindow` dependencies. Provide pkg-config stubs with AOSP headers, and link against libs pulled from the device's /system and /vendor (adb pull).
   - Use u_gralloc with the cros_gralloc (minigbm) backend, or gralloc4/IMapper, to match the vendor gralloc.
   - It also needs libdrm built with the NDK.
3. **Vendor integration:**
   - Install `/vendor/lib64/egl/libEGL_mesa.so`, `libGLESv1_CM_mesa.so` and `libGLESv2_mesa.so`, plus the gallium lib.
   - Set `ro.hardware.egl=mesa` and `debug.hwui.renderer=skiagl`. Disable blur (`ro.surface_flinger.supports_background_blur=0`).
   - Panfrost needs kmsro or a renderonly pairing with mediatek-drm (card0) for scanout buffers: Mesa's "kmsro" / panfrost + mediatek renderonly. Check that `mediatek_dri` (kmsro) maps to the mediatek KMS device.
   - Load panfrost.ko, gpu-sched.ko and drm_shmem_helper.ko early in vendor init, from `/vendor/lib/modules`, before SurfaceFlinger.
   - SELinux file contexts for the new libs (`same_process_hal_file`) and the dri device permissions (0666 like card0).
4. **Test:** SurfaceFlinger comes up with GLES from Mesa, `dumpsys SurfaceFlinger | grep GLES` shows Panfrost, and touch latency drops.

## Other open issues (not part of this task)

- Display: column bands slowly build up with any content and clear after screen off/on. They are not caused by SoC registers, panel init or backlight. The user suspects panel damage.
- Wi-Fi: DMA disabled (PIO), P2P wiphy WARN, connect untested.
- Sound: playback hangs.

Memory notes are in the auto-memory file `user-zenpad-firmware-project.md`.
