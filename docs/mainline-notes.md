# ASUS ZenPad 10 Z301ML (ASUS P00L) — kernel porting notes

Дата: 2026-11-08. **Это экспериментальная разработка, НЕ готовая прошивка.**

## Устройство и заводская база

- SoC: MediaTek MT6735/MT8735 family; arch ARM64; ядро 3.18.35.
- Сток: Android 7.0, build 14.0410.1805.70.
- `boot` — 16 MiB, Android boot image v0 с kernel+DTB и ramdisk; в конце стока есть подпись ASUS RSA, её нельзя переносить на изменённое ядро.
- Штатная конфигурация device tree: `asus8735_tb_301_n`.
- Заводские резервные копии: `~/ASUS-Z301ML-backup/`. Не стирать `nvram`, `nvdata`, `proinfo`, `persist`, `protect1/2`, `preloader` и другие уникальные разделы.
- Штатный /boot до начала экспериментов успешно сохранён в `~/ASUS-Z301ML-backup/boot.bin`.

## Воспроизведённое ядро 3.18

- Официальный ZIP ASUS: `~/ASUS-Z301ML-port/kernel-source/Z301ML-14.0410.1801.57-kernel.zip` (оригинал нетронут).
- Исходник `asus8735_tb_301_n_defconfig`, Linux 3.18.35, в `z301ml-kernel` (Lima Ubuntu ARM64).
- Собран `Image.gz-dtb`: `~/ASUS-Z301ML-port/output/Image.gz-dtb`.
- SHA-256: `1bb0a29528b1dcc3edaee27349849055d33abda4ca7c36dd05c94e905ddd5743`.
- Новый DTB **идентичен заводскому**, SHA-256 `f13d31617130eb34f874d8042d9328f19db7cf394acf45164c0d402b5a5a4538`.
- Неподписанный тестовый boot image: `~/ASUS-Z301ML-port/output/z301ml-test-boot-UNSIGNED.img`. **Не прошит, загрузка не проверена**.

## Новая экспериментальная ветка MT6735 Mainline

- Источник: `https://gitlab.com/mt6735-mainline/linux.git`.
- Ветка: `mt6735-stable-7.0.y`, commit `046883c0c2b956fd7436d3c1156f25512d1f6a90` (Linux 7.0.10).
- Исходники внутри Linux VM: `~/z301ml-port/mainline/linux-mt6735-7.0`.
- Рабочие артефакты внутри Linux VM: `~/z301ml-port/mainline/build-7.0`.
- Экспериментальный DTS: `~/ASUS-Z301ML-port/mainline/mt6735-asus-p00l.dts` (также в Linux kernel tree).
- Переносимый diff: `~/ASUS-Z301ML-port/mainline/p00l-board-v1.patch`.
- DTS компилируется в `arch/arm64/boot/dts/mediatek/mt6735-asus-p00l.dtb`, 15 KiB. **Это минимальная плата, не полная аппаратная поддержка**.
- Старый ASUS DTB из стокового /boot: `~/ASUS-Z301ML-port/output/stock-asus-p00l.dtb`.
- Начальная новая DTS включает: память `0x40000000..0x5effffff` (консервативно из stock), UART0 921600, eMMC0 до 52 MHz, ramoops; без проверенной PMIC-схемы питания.
- Сборка нового ядра: из Mac `limactl shell z301ml-kernel`, затем из Linux VM:
  ```bash
  K=$HOME/z301ml-port/mainline/linux-mt6735-7.0
  O=$HOME/z301ml-port/mainline/build-7.0
  make -C "$K" O="$O" ARCH=arm64 defconfig
  make -j3 -C "$K" O="$O" ARCH=arm64 dtbs
  make -j3 -C "$K" O="$O" ARCH=arm64 Image.gz
  ```
- Лог Linux 7 сборки: `~/z301ml-port/mainline/kernel-7.0-build.log` в VM.

## Ограничения и дальнейшие задачи

1. **До любой тестовой прошивки** подтвердить способ восстановления, проверить, поддерживает ли ASUS LK временную команду `fastboot boot`. Из анализа строк LK доступны flash/download, но поддержки `fastboot boot` пока не доказано.
2. Подробно определить PMIC / питание eMMC / память (в Android показано 2.49 GiB, а заводской статический DTS задаёт начальные 496 MiB), чтобы новый DTS не перезаписывал зарезервированные области.
3. Получить доказательство реальной загрузки минимального ядра (UART, pstore, затем USB/eMMC).
4. Под Android 15 нужна совместимая kernel-ABI/Android Binder, SELinux и адаптация HAL; Linux 7.0 mainline **не является готовой GKI Android 15**. Для Android 15 одна из базовых официальных веток — Android 15 GKI 6.6; можно рассматривать перенос SoC-патчей из mainline в совместимую Android-ветку.
5. После первых запусков сделать аккуратную интеграцию драйверов LCD, тачскрина, USB, Wi-Fi, LTE, камеры и Mali. Эти компоненты не работают автоматически от одной DTS.

**Важно: пока на планшете не было записано ни одного байта в рамках эксперимента с новым ядром.**

## Результаты сборки Linux 7.0.10 и загрузочного образа (2026-11-08)

- `make -j3 ... Image.gz`: SUCCESS, Linux 7.0.10, build `046883c0c`, размер `14,981,026` байт.
- После включения `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ANDROID_BINDER_DEVICES="binder,hwbinder,vndbinder"`, `CONFIG_PSTORE_RAM=y`, `CONFIG_PSTORE_CONSOLE=y`, `CONFIG_PSTORE_PMSG=y`, `CONFIG_DEBUG_FS=y`, `CONFIG_PRINTK_TIME=y`: повторная компиляция SUCCESS.
- Debug kernel: `~/ASUS-Z301ML-port/mainline/artifacts/linux-7.0.10-debug-binder-pstore-Image.gz`, 15,038,921 байт, SHA256 `3ff300d223241211a8e38a7082ae957e153ccd216bf1f59f29ddd11dccfe3b61`.
- Device tree: `~/ASUS-Z301ML-port/mainline/artifacts/mt6735-asus-p00l.dtb`, 14,475 байт.
- Статический ARM64 BusyBox initramfs: `~/ASUS-Z301ML-port/mainline/artifacts/initramfs.cpio.gz`, 1,049,909 байт. Запускает `/init`, выводит информацию в /dev/console.
- Диагностический **неподписанный и непроверенный** Android boot image: `~/ASUS-Z301ML-port/mainline/artifacts/linux7-diagnostic-binder-pstore-UNSIGNED-DO_NOT_FLASH.img`, 16,107,520 байт (из 16,777,216 вместимости), SHA-256 `2ed292235129a8de10a7d80224863ce0fe4d2f54d712b5ce74aa9536f38f8489`.
- Offline-проверка Android v0 boot заголовка, SHA-1 kernel+ramdisk, смещений и размера успешна. Это **НЕ доказывает**, что образ загрузится на LK/ASUS. Не прошивать до проверки регуляторов питания и процедуры recovery.

## Реальный Fastboot — обнаружен сбой

- Через ADB `adb reboot bootloader` успешно перевёл Z301ML в Fastboot. USB определяется `0b05:4daf`, `fastboot devices` показывает устройство.
- `fastboot getvar product` сначала ответил `ASUS8735_TB_301_N`.
- Следующий запрос `fastboot getvar version` завис; команда на Mac была принудительно остановлена.
- Попытка **временной, без прошивки** `fastboot boot` с **заводским** `stock-boot.img` завершилась тайм-аутом через 25 секунд.
- `fastboot reboot` тоже не получил ответа и был остановлен через 15 секунд. Вероятно, завис обработчик команд старого LK; это не подтверждённый отказ загрузчика вообще.
- **Состояние после теста**: устройство оставалось в Fastboot по USB, Android не загрузился обратно автоматически.
- Для восстановления: **отключить USB, удерживать Power 20–30 секунд, отпустить, затем нажать Power для обычного включения без кнопок громкости**. До подтверждения не утверждать, что Android снова загрузился.
- **За всё время эксперимента Linux 7.0 не выполнялись flash/write команды и не изменялось содержимое eMMC**. Команды были: adb reboot bootloader, fastboot getvar, fastboot boot штатного образа, fastboot reboot.

## 2026-11-08 — Android restored; prepared safer 3.18 recovery experiment

- After physical reboot Android 7 booted. Verified over ADB: `H6NPFP022437BJH device`, Linux 3.18.35, verifiedbootstate orange.
- Factory recovery backup remains intact: `~/ASUS-Z301ML-backup/recovery.bin`, 16 MiB, SHA-256 `7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e`.
- Built offline `~/ASUS-Z301ML-port/output/z301ml-test-recovery-318-UNSIGNED-DO_NOT_FLASH.img` using newly built 3.18.35 kernel + **unchanged stock recovery ramdisk**.
- Verified stock recovery boot header SHA-1, all offsets, rebuilt SHA-1, 16 MiB partition size limit; output 12,673,024 bytes, SHA-256 `b83a8d579253c07d951d4953c3f434685c7f8b5f8bde4222b734e94ff4c44cf4`.
- This test file is UNSIGNED and NOT YET FLASHED. The original ASUS RSA footer is not reusable.
- For safer initial testing, keep original boot partition untouched; recovery can be restored with MTKClient after entering the MediaTek preloader/BROM. The Fastboot command loop on this LK previously hung, so do not rely on Fastboot for recovery.
- Caution: changing the recovery partition is a real flash write. Confirm known-good MTKClient procedure and hardware USB recovery entry before attempting it.

## 2026-11-08 — Recovery 3.18.35 flash succeeded (VERIFIED)

- MTKClient connected to live Legacy Download Agent on USB 0e8d:2001, no new BROM handshake.
- Preflash read of exactly GPT recovery at LBA 191488, 32768 sectors (offset 0x5d80000, 16 MiB), SHA256 7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e matched original backed-up recovery.
- Flashed ONLY recovery from ~/ASUS-Z301ML-port/output/z301ml-test-recovery-318-FULL16MiB-UNSIGNED-DO_NOT_FLASH.img. This image has custom ASUS-source Linux 3.18.35 kernel + stock recovery ramdisk, NO original ASUS RSA signature.
- Readback into ~/ASUS-Z301ML-port/mainline/recovery-readcheck/recovery-live-after-flash.bin was 16 MiB and SHA256 e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2 — EXACT MATCH of experimental image.
- Live log ~/ASUS-Z301ML-port/mainline/recovery-readcheck/guarded-flash-second.log. Original recovery backup preserved, SHA256 7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e.
- Main boot PARTITION NOT TOUCHED. Device not rebooted yet as of readback verification. This is flash success only, NOT proof kernel boots. [CORRECTED: Power works; only Volume+ broken]; DA reset may leave the tablet off and require manual power-on/reconnect. Inspect and plan controlled boot and rollback before using DA reset.


## 2026-11-08 — USB monitor and Linux 7 mainline bring-up V2

### USB
- DALegacy.finish() bug patched in ~/mtkclient/mtkclient/Library/DA/legacy/dalegacy_lib.py; saved original dalegacy_lib.py.before-z301ml-finish-fix. Old bug compared integer ACK to bytes using identity.
- Sent pending DA HOME_SCREEN mode argument 00000001 (4 bytes), ACK received 0x5A. Log recovery-readcheck/da-pending-arg-second.log.
- One USB reset returned [Errno 60] Operation timed out; USB device disappeared. This DOES NOT prove boot.
- 90 read-only samples every 2 seconds, 17:13:46–17:16:47 local; ioreg, adb devices, fastboot devices. NO DEVICE EVER APPEARED. Logs usb-monitor-180s.log and usb-monitor-180s.jsonl.
- Physical recovery needed if device remains absent. [CORRECTED by user: Power button WORKS; only Volume+ is broken]. Do not disconnect battery without safe procedure or write boot.
- Stock Android boot partition untouched. Recovery contains experimental 3.18.35 kernel, flash SHA verified; real boot untested.

### Display
- Factory LK strings identify candidate LCMs: nt35523_wxga_dsi_vdo_boe, otm1287a_wxga_dsi_vdo_kd, hx8279d_fhd_dsi_vdo_boe, hx8279d_fhd_dsi_vdo_kd. LK contains videolfb - fb_base = 0x%llx and lcm=%1d-%s strings.
- ASUS official Z301ML specs: 1280 x 800 WXGA, model usually MT8735W; Z301MFL is Full HD MT8735A. https://www.asus.com/cz/news/finerpqtnxjljsvy/
- For P00L Z301ML actual candidate LCD likely NT35523 BOE or OTM1287A KD. Exact controller, LK framebuffer physical base and stride unknown. Do not invent values.

### Linux 7.0.10 mainline V2 build on Ubuntu Lima
- Kernel tree in VM: ~/z301ml-port/mainline/linux-mt6735-7.0. Build dir ~/z301ml-port/mainline/build-7.0. Kernel repository MT6735 mainline branch mt6735-stable-7.0.y, commit 046883c0c2b956fd7436d3c1156f25512d1f6a90.
- Board DTS V2: ~/ASUS-Z301ML-port/mainline/mt6735-asus-p00l-v2.dts (and in VM kernel tree). Compiled DTB 15,023 B SHA256 75333815354da066c66d998efd91dce9310b248ffeffa23656e58a364f7a2f77.
- DTS V2: MSDC0 x8 eMMC; MSDC1 x4 microSD; I2C1 FocalTech FT5826 at 0x38 IRQ GPIO10 reset GPIO131 (driver node intentionally disabled); USB MUSB at 0x11200000 with TPHY at 0x11210000; 496 MiB initial RAM, ATF/ramoops/minirdump reserved; simple-framebuffer placeholder intentionally DISABLED because LK framebuffer address/stride unknown.
- Built-in kernel symbols include USB_MUSB_MEDIATEK, USB_CONFIGFS, USB_F_ACM, USB_F_RNDIS, USB_F_ECM, MMC_MTK, FB_SIMPLE, PSTORE_RAM. Full config artifacts/linux-7.0.10-v2.config.
- Kernel artifacts/linux-7.0.10-v2-Image.gz: 15,130,994 B SHA256 e0dadc98447ede0b01b3989ce1100df4e79fab6ae2f81981c0a0e38b11b016bb.
- Kernel+DTB artifacts/linux-7.0.10-v2-Image.gz-dtb: 15,146,017 B SHA256 5b45fb963b79f40860f8be904d25ab77fbcab33bdb1f44f5ae91104e479217b5.
- ARM64 BusyBox initramfs artifacts/initramfs-gadget-v2.cpio.gz: 1,050,820 B SHA256 8c348708115c29516bb8d3269cdde2b7d07b6e99df7c7a7f33d627fdfdec738d. Shell source init-mainline-gadget-v2.sh configures ACM+ECM for macOS, ACM+RNDIS, attempts USB ttyGS0 shell, prints kernel and USB diagnostics, does not mount user partitions read-write.
- Recovery image artifacts/linux7-v2-gadget-ACM-ECM-RNDIS-recovery-UNSIGNED-DO_NOT_FLASH.img: 16,201,728 B, 575,488 B below partition maximum, SHA256 7d5365494339d88eb87740647401bb35278bcd8a9d3dd4a9721f588311e48adb. Repacked with factory recovery header via repack_diag_recovery_v2.py; Android v0 SHA1, offsets, gzip kernel, FDT, newc RAMDISK and builtin config all independently verified.
- V2 source patch p00l-board-v2.patch; kernel build logs v2-kernel-build.log and v2-dtbs-build.log inside VM.
- Linux 7 recovery image is UNSIGNED, UNFLASHED, and untested on hardware. NEVER write boot. Before attempting any new flash: regain reliable hardware connection and boot-test current 3.18.35 recovery with rollback plan.
- Android 15 remains a separate userspace/HAL integration task requiring correct vendor drivers, power/clock tree, SELinux/Binder, GPU/display, and services. Linux 7 branch is not Android 15 GKI and build success does not establish Android 15 compatibility.


## 2026-11-08 17:35–17:40 — Recovered DA again, corrected FINISH succeeds

- User used MTKClient `printgpt` in fresh BROM session: Kamakiri bypass + Legacy DA stage 1/2 uploaded successfully; full GPT printed, matching `boot` offset 0x4d80000 16 MiB, `recovery` offset 0x5d80000 16 MiB.
- Mac USB confirmed `0e8d:2001`, patched Legacy DA state with matching MEID. No eMMC writes during `printgpt`.
- `da_exit_to_android.py` modified to call corrected `DALegacy.finish(1)` and print actual ACK Boolean; verified dry-run. Executed in Mac Terminal, output: `DA FINISH HOME_SCREEN ACK accepted: True` and `Transport reset attempted`. Log: `recovery-readcheck/da-exit-fresh-20261108.log`.
- After DA FINISH + transport reset, tablet disappeared from USB. ADB and Fastboot show no devices. Follow-up 40s / 20 samples USB/ADB/Fastboot monitor showed no re-enumeration. Log: `recovery-readcheck/usb-post-finish.log`.
- Interpretation: DA correctly received HOME_SCREEN exit this time. This DOES NOT prove Android or experimental recovery booted. Tablet may be off or stalled in early boot, needs physical power-on/inspection. Volume+ is BROKEN; DO NOT request using Volume+. Power button functionality has been questionable. Enter BROM with Volume- only on a powered-off device when needed.
- 3.18.35 experimental recovery remains the last SHA256-verified flash; Android boot partition NOT altered; Linux 7.0 V2 remains unflashed.

## 2026-11-08 18:00–18:39 — confirmed Recovery + para BCB and attempted DA normal finish
- User configured passwordless sudo for FULL path /Users/matveysazhnov/mtkclient/.venv/bin/python. Always run: sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u SCRIPT (not python3).
- Live read in existing DA: recovery 16,777,216 bytes SHA256 e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2, EXACT match of experimental 3.18.35 image; file recovery-readcheck/live-recovery-1800.bin.
- Live para read 524,288 bytes SHA256 25464b97ab1d4790bab32a580de8e06649d9985deba118e1415a368fcd0e45f3, backup recovery-readcheck/live-para-backup-1800.bin. First 32 bytes BCB command 0x00; nonzero other sectors at 0xa00 and 0x20000 onwards with ENV_v1 and off-mode-charge=1. LK binary strings include mboot_recovery_load_misc, para and boot-recovery; standard Android bootloader_message offset 0 command field 32 bytes.
- Wrote ONLY 512-byte first sector to para GPT at 0x4d00000. Command boot-recovery + NUL padding at relative offset 0, changed just the first 13 bytes; verified all 524,288 bytes after readback, remainder byte-for-byte unchanged. Backup SHA256 above; AFTER para SHA256 5b621a57fcd12644e542f2aab563e2b00289ff4bd38c0bed0ba6236c47a28680. Script guarded_para_boot_recovery.py, log recovery-readcheck/para-guard-write-1800.log. Original sector backed up para-original-sector-512-guard.bin. Recovery was NOT changed.
- Ran corrected DA finish(0) NORMAL only after a live 512-byte para sector reread confirmed boot-recovery. Output FINISH(0) ACK: True; log recovery-readcheck/da-finish0-after-boot-recovery.log. No other eMMC writes in this step.
- 120s USB monitor before/during/after: 60 samples 18:36:45–18:38:45 (Asia/Aqtobe). Started USB 0e8d:2001; changed to NO USB at 18:37:05; NEVER appeared in USB, ADB or Fastboot afterward. Logs recovery-readcheck/usb-after-para-finish0-120s.log and .jsonl. DA accepted finish(0) but boot of Recovery was NOT verified, and the tablet is physically absent from USB. Likely powered off or early boot/charging (KPOC); cannot determine precisely without physical inspection.
- Original boot partition remains untouched. Experimental kernel recovery remains on eMMC. BCB boot-recovery may persist until recovery clears it and can cause boot loops if recovery does not work.
- Guarded original BCB restore script is ready at mainline/restore_para_bcb_guarded.py (requires new BROM session) to restore para sector only and verify complete 512KiB SHA against backup; it was NOT RUN.
- Physical button constraints: Volume+ BROKEN, [CORRECTED: Power works; only Volume+ broken]. For next BROM, UNPLUG data USB then hold ONLY Volume- while plugging USB. No Volume+.

## 2026-11-08 18:53–19:45 — boot path solved, kernel handover investigated

**Buttons (user-confirmed): ONLY Volume+ is broken. Power WORKS. Volume− works (BROM = hold Vol−, then plug USB).**

- `para` ENV (MTK LK `ENV_v1` at para+0x20000, data to tail sig at +0x23ff4, checksum u32 LE at +0x23ffc = byte-sum of data) had `off-mode-charge=1`. Changed to `0` with `guarded_para_offmodecharge0.py` (2 sectors, full readback). Result: plugging USB now powers on and BOOTS (no KPOC charging).
- Confirmed chain: USB plug → preloader `0e8d:2000` (~3 s) → LK → para BCB `boot-recovery` → recovery partition.
- Stock recovery boots ("No command"). Stock recovery with its AVB1 `BootSignature` tail ZEROED (`artifacts/stock-recovery-SIGSTRIPPED-test.img`) ALSO boots → LK (orange) does NOT require signature.
- Stock Android at boot runs `flash_recovery` and silently REWRITES recovery to stock (observed: SHA 8834d45f…, identical image area). Therefore always flash recovery + BCB in ONE DA session (`flash_recovery_and_bcb.py IMAGE`), so Android never runs in between.
- Stock Android boots with ADB already authorized (`0b05:7773`, serial H6NPFP022437BJH). `adb reboot recovery` works. Framebuffer 800x1280 portrait, stride 3200, 32 bpp. `ro.boot.lcm_id=0` (LK list order suggests nt35523_wxga_dsi_vdo_boe — unconfirmed). Saved `android-info/`.
- Our 3.18.35 (GCC 15.3) and Linux 7.0.10 v2 both WDT-loop every ~31 s (`kedump: boot_reason(3)`, `wdt_status 0x5`), RAM console 0x43f00000 empty → die before printk/pstore. Stock kernel decompresses to 0x11a97e0; ours 3.18 = 0x13283d8, Linux7 = 0x2825a00 (40 MB). Hypotheses: LK kernel decompress size limit; GCC 15 for 3.18. Building slim Linux 7 (ARCH_MEDIATEK only, no modules) in VM dir build-slim.
- Tools: `usb_watch.sh SECONDS` (passive USB/adb/fastboot change log), `da_finish0_simple.py`, `flash_recovery_image.py`, `flash_recovery_and_bcb.py`. Catching the WDT loop needs Vol− held (preloader handshake too short).

## 2026-11-08 19:45–21:05 — LINUX 7.0 BOOTS TO USERSPACE ON Z301ML

Root causes found by bisection (fake kernels: S1–S4, loop period 31 s = LK never jumped, 22 s = our code ran):
1. **Stock LK does not jump into a kernel whose gzip stream is small.** S2 (stock header + reset code + zeros, gz 18 KB) → no; S3 (same + random padding, gz ≈ 7.8 MB like stock) → yes. Fix: `mkpadded.py` (pad decompressed blob with random bytes so gz ≈ stock size, then append DTB).
2. **Stock LK rejects a plain mainline DTB.** Stock DTB → OK; mainline v2 DTB → loop. Hybrid **v5** DTB (root compatible + `mediatek,MT6735`, model, factory-named reserved-memory nodes atf/ram_console/minirdump + dynamic ccci_md1/consys, `/firmware/android`) → accepted.
3. arm64 `text_offset=0` kernel needs a 2 MiB-aligned load; LK loads at 0x40080000 → use **zimage64** shim (github external-mirrors/zimage64, built in VM `~/z301ml-port/mainline/zimage64`), RELOCATABLE kernel, 1 CPU (secondaries broken via firmware, as in doogee-x5pro DTS).
4. LK REPLACES the kernel cmdline; use `/chosen/zimage64,cmdline-override`.
5. zimage64 DT paths must start with `/` (root node has empty name).

Tools: `probe/fbprobe*.S` payloads (WDT off / OVL0 scanout addr from 0x14007000 SRC_CON+0xf40 → paint green, patch simplefb reg). `mkpadded.py`, `pack_recovery.py`, `catch_and_flash.sh IMAGE` (wait BROM → flash recovery + BCB → finish).

**Log capture method:** ramoops console zone at 0x43f10000 inside LK kedump window (0x43f00000..+0x80000); initramfs v3 opens /dev/watchdog after 20 s → HW WDT reset → LK copies window to expdb (`SYS_RAMCONSOLE_RAW` at expdb+0xa00) → catch BROM (Vol−) → `mtk r expdb` → console zone at +0x10000, header `DBGC`. First full log: `crashlogs/linux7-console.txt`.

First boot log (v6): Linux 7.0.10 tiny boots, initramfs `/init` runs at 0.19 s, mtk-wdt, ttyS0, pstore OK, simplefb registered (addr 0 → payload path bug), clocks/PDs disabled (cmdline replaced), eMMC `no support for card's volts` (no vmmc/vqmmc), MUSB `DMA controller not set` (-19). v7 fixes: MT6328 regulators + supplies, USB_INVENTRA_DMA, cmdline-override, fb reserve, `/` paths.

## 2026-11-08 21:12 — v8: PERSISTENT LINUX 7.0 WITH USB SHELL (milestone)

Image: `artifacts/L7-v8-usbshell-FULL16MiB.img` (zimage64 + fbprobe4 payload, tiny kernel #7 with pwrap IRQ fix, DTB v7(+fbcon rotate) = `artifacts/mt6735-asus-p00l-v8.dtb`, initramfs `initramfs-usbshell-v4`). Flashed to recovery + BCB `boot-recovery`.

Working (from `crashlogs/linux7-v8-dmesg-usb.txt`, captured over USB):
- cmdline-override applied (clk/pd/regulator_ignore_unused, fbcon=rotate:1)
- simple-framebuffer at LK scanout **0xff638000**, 800x1280 a8r8g8b8, linelength 3200 → fbcon on panel (panel itself shows stripes = hardware)
- **eMMC**: `mmcblk0: HBG4a2 29.1 GiB`, all 32 GPT partitions + boot0/boot1/rpmb (MT6328 vemc33/vio18 supplies)
- **USB gadget** (MUSB + INVENTRA DMA): ACM `/dev/cu.usbmodem1101` (shell) + ECM network on Mac
- mtk-wdt, pstore/ramoops, ttyS0, MT6328 PMIC via pwrap (bit1 IRQ masked; one `int=0x1` remains)
- 1 CPU only (secondaries removed, as doogee-x5pro)

Shell helpers: `/tmp/ttycmd.py`-style pyserial (mtkclient venv) on `/dev/cu.usbmodem*`.
To return to stock Android: in DA run `restore_para_bcb_guarded.py`-style clear of para BCB (or write zeros to para[0:32]); Android's flash_recovery will then restore stock recovery itself.
Not yet: display driver (DSI/OVL, panel nt35523 likely), touch FT5826, SMP, cpufreq/thermal, battery/charger, audio, Wi-Fi/BT (consys), GPU Mali-T720 (panfrost), modem.

## 2026-11-08 21:26 — v10: ALL 4 CPUs (SMP) WORKING

Cause: stock ATF accepts PSCI CPU_ON but does not power the core MTCMOS; vendor 3.18 `enable-method="mt-boot"` (drivers/misc/mediatek/base/power/mt6735/mt_psci.c) calls PSCI then `spm_mtcmos_ctrl_cpu(cpu, STA_POWER_ON)`.
Fix: `arch/arm64/kernel/psci.c` → after successful CPU_ON on `mediatek,mt6735`, `mt6735_mtcmos_cpu_on()` (SPM 0x10006000: CA7_CPUn_PWR_CON 0x218/0x21c/0x220, L1_PDN 0x264/0x26c/0x274, PWR_STATUS(_2ND) 0x60c/0x610 bits 12/11/10; ON → ON_2ND → wait status → clear ISO → clear L1_PDN, wait ACK → SRAM_ISOINT_B, clear SRAM_CKISO, clear CLK_DIS → set RST_B), timeouts on all waits. CPU1-3 nodes restored (v10 DTS, no maxcpus).
Verified: `smp: Brought up 1 node, 4 CPUs` at 0.006 s; 4-way busy loop at 100% usr stable.
Image: `artifacts/L7-v10-smp4-FULL16MiB.img`. Kernel patch (all board changes so far): `p00l-board-v10.patch`; config `artifacts/linux-7.0.10-tiny-v10.config`.
Live shell helper: `ttyq.py 'CMD' [timeout]` (pyserial on /dev/cu.usbmodem*).

## 2026-11-08 21:33 — v11: TOUCHSCREEN (FocalTech FT5826) WORKING

- Stock: `mtk-tpd,ft5826` @ I2C1 0x38, INT GPIO10 (EINT, falling), RST GPIO131, power `vtouch-supply` = MT6328 **VGP1** (2.8 V). Vendor driver: kernel-3.18 drivers/input/touchscreen/mediatek/ft5826.
- Mainline: `edt-ft5x06` (compatible `focaltech,ft5426`) GENERIC_FT path, chip ID reg 0xA8 = 0x3b → `input: generic ft5x06 (3b)` = /dev/input/event0. `vcc-supply = <&mt6328_vgp1_reg>`, pinctrl GPIO10 input pull-up / GPIO131 output-high. Config: INPUT_TOUCHSCREEN, TOUCHSCREEN_EDT_FT5X06.
- Verified on device: IRQ counter rises (`mt-eint 10 Edge ft5426`), multi-touch TD_STATUS up to 5 points, ABS_MT_POSITION_X/Y events stream (59 KB / 8 s).
- Axes: a swipe along one edge gave Y 7..796 → touch Y = panel width; touch is landscape-oriented relative to the 800x1280 portrait panel. DTS v11 updated (not yet re-flashed) to size 1280x800 + `touchscreen-swapped-x-y`; inversion to be confirmed once a real display driver/UI exists.
- Image: `artifacts/L7-v11-touch-FULL16MiB.img`; patch `p00l-board-v11.patch`.

## 2026-11-08/09 — v15: DSI DISPLAY VIA MEDIATEK-DRM WORKING

- Panel identified from `/proc/device-tree/chosen/atag,videolfb` lcmname: **nt35523_wxga_dsi_vdo_boe** (old rev, `BOE_HD_LCM=0`); LK fb_base 0xff250000, fps 58.81.
- New driver `drivers/gpu/drm/panel/panel-boe-nt35523-p00l.c` (compatible `asus,z301ml-boe-nt35523`): init sequence generated from vendor kernel-3.18 lcm table; power = MT6328 VRF18_1 + GPIO147, reset GPIO146 (active-low), 4 lanes RGB888 burst video, non-continuous clock, 800x1280@60 (HSA16/HBP48/HFP16, VSA4/VBP12/VFP16). Backlight: pwm-backlight on disp-pwm + GPIO3.
- Pipeline OVL→COLOR→DITHER→RDMA0→DSI0 (+mutex, mipi-tx) enabled with aliases.
- Hangs fixed along the way: v12 M4U under live LK scanout → `/delete-property/ iommus` on ovl/rdma + m4u disabled (CMA 64M used); v13/v14 `mtk_dsi_bind()` → `device_reset_optional()` reset of live DSI hung bus (RCU stall CPU3) → `/delete-property/ resets` on dsi; scpsys DIS domain made `MTK_SCPD_ALWAYS_ON`.
- Result: `[drm] Initialized mediatek 1.0.0`, `fb1: mediatekdrmfb`, `NT35523 BOE panel initialised`, `/dev/dri/card0`, `/sys/class/backlight/backlight` (max 1023).
- Fast iteration: `flash_from_linux.py IMAGE` (USB ECM link-local + wget + dd to PARTNAME=recovery + sha readback + reboot) — no BROM needed while a working Linux is running. Recovery path on bootloop: `catch_log_and_flash.sh IMAGE TAG --force-unknown` (Vol− BROM → read expdb log → flash).
- Patch: `p00l-board-v15.patch`; image `artifacts/L7-v15-dsi-noreset-FULL16MiB.img`.
- TODO: confirm colours/orientation visually, enable IOMMU properly (stop LK scanout before M4U), re-enable DSI reset after clean handover, drop simplefb.

## 2026-11-09 — v16: DISPLAY VERIFIED BY EYE

- Previous colour test wrote into a regular file: kernel lacked `CONFIG_FB_DEVICE` (no /dev/fb* char devices). v16 adds FB_DEVICE + DEVMEM.
- `/dev/fb1` = mediatekdrmfb 800x1280 32bpp stride 3200 (fb0 = simplefb). Full-screen red/green/blue/white shown with CORRECT colours (XRGB8888 LE: bytes B,G,R,X); pwm-backlight 1023/30/600 visibly changes brightness. User-confirmed.
- eMMC block index is not stable (mmcblk0 or mmcblk1 depending on probe order) → `flash_from_linux.py` now locates the partition by `PARTNAME=recovery`. TODO: DT aliases mmc0=&mmc0, mmc1=&mmc1.
- Image `artifacts/L7-v16-fbdev-FULL16MiB.img`; patch `p00l-board-v16.patch`.

## 2026-11-09 — v17/v18: CHARGER (BQ25896) + BATTERY GAUGE

- Vendor `TI,sn2870` @ i2c3 (0x1100f000) 0x6b is a **TI BQ25896** (mainline `bq25890_charger` identifies it). Same bus: TS3A225E 0x3b, LP8557 0x2c (both silent on probe).
- DT (v17): `ti,bq25890` with vendor values (VREG 4.368 V, ICHG 2.176 A, ITERM 128 mA, IPRECHG 384 mA, SYSMIN 3.6 V, boost 5.19 V/1.2 A), `linux,skip-reset`; IRQ = ACOK GPIO98 (vendor polled, no INT in DT). Also aliases mmc0/mmc1 → eMMC is mmcblk0 again.
- Verified: `bq25890-charger-0` Charging/Fast, VBAT 4.324 V, TS 31.0 °C, input limit 500 mA from Mac USB.
- v18: new `drivers/power/supply/z301ml-battery.c` (`asus,z301ml-battery`): battery power_supply fed from charger VBAT/IBAT/TS/status; capacity via `simple-battery` OCV table = vendor `lg_battery_profile_t2` (25 °C; batt ID 100 = LG is vendor default), design 4558 mAh (`q_max_pos_25`), IR compensation 120 mΩ while charging, EMA smoothing, 10 s poll + external_power_changed.
- Verified: `/sys/class/power_supply/battery` CAPACITY 88 %, Charging, 31 °C.
- TODO: CURRENT_NOW reads 0 (bq ADC/IBAT), read real batt ID (APL6001), temperature-dependent OCV tables, coulomb counting.
- Patch `p00l-board-v18.patch`; image `artifacts/L7-v18-battery-FULL16MiB.img`.

## 2026-11-09 — v19/v20: CPU DVFS 299–1300 MHz WORKING

- Stock table (from stock Android dmesg + vendor mt_cpufreq.c, MT6735 CPU_LEVEL_1 "1.3GHz segment"): 1300@1.25 V, 1235@1.23125, 1170@1.20625, 1040@1.15, 819@1.10, 598@1.05, 442@1.00, 299@0.95 V. LK boots at 819 MHz, VPROC 1.15 V.
- **Mainline bug fixed**: `drivers/regulator/mt6328-regulator.c` buck_vproc used `MT6328_VPA_CON11` as VOSEL → read 0.6 V. Correct `MT6328_VPROC_CON11` (LK leaves VOSEL_CTRL=0, SW mode). Now reads 1.15 V.
- New `drivers/cpufreq/mt6735-cpufreq.c` (ARM_MT6735_CPUFREQ): vendor sequence — AP_PLL_CON2[5]=1 (MAINPLL core CK), TOP_CKMUXSEL(0x10000000)[3:2]=2 (MAINPLL), ARMPLL_CON1(0x10209204)=vendor DDS|CHG, 20 µs, mux back to ARMPLL (1); VPROC raised before / lowered after; one policy for CPUs 0-3. DT: `&cpu0 { proc-supply = <&mt6328_vproc_reg>; }`.
- Verified: each step changes cpuinfo_cur_freq + VPROC; busy-loop time 1.99 s @819 → 1.26 s @1300 (ratio 1.58 = 1300/819); 299 MHz@0.95 V ↔ 1300 MHz@1.25 V; 30 s 4-core stress @1.3 GHz stable.
- v20: default governor schedutil — idle 299 MHz, load 1300 MHz, back to 299 MHz.
- TODO: thermal zone + cooling (no SoC temp sensor driver yet, driver flagged CPUFREQ_IS_COOLING_DEV), efuse segment check, FHCTL hopping (not needed).
- Image `artifacts/L7-v20-schedutil-FULL16MiB.img`; patch `p00l-board-v20.patch`.

## 2026-11-09 — v21: SoC THERMAL SENSOR + CPU THROTTLING

- No MT6735 support in tree; added `mt6735_thermal_data` to `drivers/thermal/mediatek/auxadc_thermal.c` (vendor mtk_tc_D1.c): 3 banks x1 sensor (Bank0 CPU=TS2, Bank1 SOC/GPU=TS1, Bank2 LTE=TS3), mux {0,1,2}, AUXADC ch 11, calib v1, cali 165, TS_CON1[5:4]=00 to power sensors. `mediatek,mt6735-auxadc` added to mt6577_auxadc.
- eFuse calib cell 0x19c (12 bytes) — live values valid: DEGC_CALI 60, VTS 227/228/224, ADC_GE 513.
- DT v21: efuse/auxadc/thermal nodes, `cpu-thermal` zone (passive 85 °C → cpufreq cooling, critical 110 °C), `#cooling-cells` on cpu0.
- Verified: idle 35–36 °C; 60 s 4-core @1.3 GHz → 55.7 °C; 10 s after → 38.9 °C. cooling_device0 = cpufreq-cpu0 (8 states).
- Patch `p00l-board-v21.patch`; image `artifacts/L7-v21-thermal-FULL16MiB.img`.

## Android 15 GSI bring-up (2026-11-09 night)

Layout: recovery(p9) = rescue Linux v22 · boot(p8) = Android kernel (A*) · system(p29) = AOSP GSI
`aosp_arm64-exp-BP11.241210.004` (written raw, SHA verified; stock Android 7 system NOT backed up, user's call) ·
cache(p30) = homemade vendor (ext4) · userdata(p31) = wiped, auto-formatted by fs_mgr (`formattable`).

Boot path (legacy SAR via pre-init ramdisk, `android/work/ard/init`, static busybox):
mount devtmpfs/proc/sys → **re-arm BCB `boot-recovery`** in para (so any reboot returns to rescue Linux) →
take wakelock `z301ml_bringup` → mount p29 ro at /newroot → `switch_root /newroot /init` (GSI `/init -> /system/bin/init`).
First stage: DT fstab `/firmware/android/fstab/vendor` (cache, by-name via `androidboot.boot_devices=soc/11230000.mmc`).
SELinux: kernel `SECURITY_SELINUX_DEVELOP=y` + patch in `selinuxfs.c sel_write_enforce` (Z301ML_FORCE_PERMISSIVE) → stays permissive.
Policy: runtime secilc compile, vendor `plat_sepolicy_vers.txt = 202404` (34.0 mapping needs plat_pub_versioned; 202404 is self-contained), empty vendor cil.

Kernel: `android.frag` + AOSP `android-6.6/android-base.config` + PROC_SYSCTL, CPUSETS_V1, MEMCG_V1,
**BLK_DEV_WRITE_MOUNTED=y** (else every APEX mount = EBUSY), EROFS_FS_ZIP, COMPAT (zygote64_32). DTS `mt6735-asus-p00l-android.dts`
(includes v21, Android cmdline, DT fstab). Build: `android/build_android_kernel.sh TAG`.

Vendor (`android/work/vendor`, build `android/build_vendor.sh`): build.prop overrides `ro.debuggable=1 ro.adb.secure=0 ro.secure=0`
(vendor props override system in A15 init), `ro.zygote=zygote64_32`, `persist.sys.usb.config=adb`; fstab.mt6735; init.mt6735.rc
(logs: `/data/vendor/log/{dmesg-early,dmesg,logcat}.txt`, autoreboot after 7 min unless `/data/vendor/keep`);
init.mt6735.usb.rc (configfs g1 on `musb-hdrc.4.auto`, f9 = ACM root console `/vendor/bin/rootcon.sh`, f1 = adb).
**KeyMint**: GSI keystore2 aborts without TEE KeyMint → `vendor/etc/patches/libkm_compat.so` = GSI lib with `cbz w0` @0x2b804
patched to `b` (TEE request gets km_compat's software KeyMint), bind-mounted over /system/lib64 in `on init`.

Iterate (tablet in rescue Linux): `android/android_try.sh mainline/artifacts/A4-android-boot-FULL16MiB.img [android/work/vendor.img]`
→ flashes boot (+vendor) over USB-ECM HTTP, verifies SHA, clears BCB, reboots, waits, dumps pstore to /tmp/android-last.log.

Progress: A1 died at kptr_restrict (no PROC_SYSCTL) · A2 APEX EBUSY · A3 /data formatted+mounted, apexd OK, keystore2 abort loop
→ km_compat patch → keystore2 no longer kills boot, Android stays up (>20 min) but USB gadget never finishes enumeration on Mac
(`!registered`). Suspect Android autosuspend (system_suspend) on a board without working resume → A4 adds permanent wakelock.

## Sound plan (started 2026-11-09)
Vendor: `kernel-3.18/sound/soc/mediatek/mt_soc_audio_v3` (AFE + `mt_soc_codec_63xx.c` = MT6328 analog via pwrap).
Stock DT: AFE @0x11220000 (`mediatek,audio`), ext speaker amp enable **GPIO9**, headset amp GPIO95, accdet `mediatek,mt6735-accdet`.
AFE register map vs mainline `sound/soc/mediatek/mt6797/mt6797-reg.h`: 161 offsets identical, only AFE_CONN7..10 differ
(v3: 0x460/0x464/0x468/0x46c vs 6797: 0x420/0x438/0x440/0x444), 90 6797 regs absent on 6735.
→ plan: `sound/soc/mediatek/mt6735/` = adapted copy of mt6797 (memif DL1/DL2/VUL/AWB, ADDA DAI, clocks: infra audio,
top audio_sel/audintbus_sel/aud1/aud2), new codec `codecs/mt6328.c` (DAC + LOL/HP drivers from vendor sequences, regmap via
pwrap), machine `mt6735-mt6328.c` with speaker amp GPIO9. Test from rescue Linux with `aplay`/`speaker-test`.

### State at end of night (2026-11-09 ~03:30)
- Tablet dropped off USB entirely during A4 run (hung or powered off). Recovery: press/hold Power → boots rescue Linux (BCB is armed).
- Ready to flash next: `mainline/artifacts/A6-android-boot-FULL16MiB.img` (Android kernel + sound drivers, pre-init with
  wakelock + hardware-watchdog guard: auto hard-reset to rescue after ~10 min unless `/data/vendor/keep`) and
  `android/work/vendor.img` (known USB identity 1d6b:0104 so macOS accessory approval isn't needed, diag service,
  autoreboot, logcat/dmesg to /data/vendor/log).
- Sound test slot: `mainline/artifacts/S1-oneshot-sound-FULL16MiB.img` = A6 kernel + rescue shell + tinyalsa + /sine1k.wav,
  boots from boot partition once and re-arms BCB to recovery.
- New kernel code: `sound/soc/mediatek/mt6735/` (AFE, adapted mt6797), `sound/soc/codecs/mt6328.c`, machine
  `mt6735-mt6328.c` (ext amp GPIO9), MFD cell `mt6328-sound`, DTS `mt6735-asus-p00l-v23.dts`. Compiles, untested.

### 2026-11-09 midday: Android 15 boots to adb (root) on its own
- Kernel Oops (corrupted kernel PTE, ksoftirqd) was the AFE: bootloader leaves memifs/DMA enabled; once audio clocks run it
  scribbles RAM. Fix in `mt6735_afe_runtime_resume`: write 0 to AFE_DAC_CON0/AFE_IRQ_MCU_CON first. Sound now built as modules
  (CONFIG_MODULES=y, MODVERSIONS off); Android kernel A10 does not load them.
- keystore2 hang: libkeymint `GetVendorPatchlevel()` blocks forever waiting for `ro.vendor.build.security_patch`
  → added it + `ro.vendor.boot_security_patch` to vendor build.prop.
- adb: `vendor/bin/usb_adb.sh` (exec with `seclabel u:r:shell:s0` — init refuses exec without a domain even in permissive)
  rebuilds config b.1 = f1 ffs.adb + f9 ACM, rebinds UDC. macOS must approve the new USB accessory once (dialog on the Mac).
- Result: reboot → `adb devices` shows `P00L-LINUX7-TEST device` in ~60 s, `adb shell` is uid 0. zygote/adbd/keystore2 run;
  surfaceflinger restarts (no composer HAL yet). Note: a network TV at 10.111.92.119:5555 also appears in `adb devices` — ignore.
- Write vendor from Android: `blockdev --setrw /dev/block/mmcblk0p30` then dd. Boot straight to Android again: zero para BCB, reboot.
- Watchdog guard still returns to rescue after 10 min unless `/data/vendor/keep` exists (`adb shell touch /data/vendor/keep`).

### 2026-11-09 afternoon: Android 15 UI (sys.boot_completed=1, lock screen + Launcher3)
Graphics/HALs = vendor APEXes from Cuttlefish arm64 Android 15 build 13263448 (ci.android.com aosp-android-latest-release,
`aosp_cf_arm64_only_phone-img-13263448.zip`, super.img unpacked with own simg2img/lpunpack python): drm_hwcomposer (hwc3),
cf.gralloc (minigbm allocator; mapper.minigbm.so + deps copied to vendor/lib64), cf.vulkan (SwiftShader `pastel`, ANGLE on top),
cf.health, audio (AIDL example HAL + cf audio policy xmls), power, thermal, memtrack, vibrator, sensors. cf.light removed (crashes).
Props: ro.hardware.egl=angle, vulkan=pastel, gralloc=minigbm, hwcomposer=drm, ro.zygote=zygote64 (32-bit procs SIGSEGV — TODO).
Fixes that were needed:
- SELinux: APEX binaries carry Cuttlefish labels (hal_*_default_exec); vendor_sepolicy.cil now declares those domains + typetransition
  from init (init refuses to start services without a domain even in permissive).
- DRM master: minigbm opened card0 first and became master → hwc went headless 1024x768 → screen showed fbcon buffer.
  Kernel: mediatek-drm gets DRIVER_RENDER, dumb ioctls DRM_RENDER_ALLOW (drm_ioctl.c) → minigbm uses renderD128, hwc owns card0.
- No ashmem in mainline: init.rc forces sys.use_memfd=false in post-fs-data → vendor rc `on property:sys.use_memfd=false` sets true.
- Power HAL required by HintManagerService; Light HAL declared-but-dead blocks LightsService (watchdog kill) → don't ship cf.light.
Known issues: vertical streak artifacts on panel (scanout vs CPU rendering, no sync framework); adb large pushes break USB
(`Error while reading USB block`) → write vendor from rescue (android_try.sh); WDT guard keep-file not seen + board hung instead of reset.
Kernel image: artifacts/A11-android-boot-FULL16MiB.img. Screenshot: android/first-ui-screenshot.png.

### Panel streaks investigation (2026-11-09 evening, unresolved)
Symptom: vertical streaks/columns (incl. blue tint) above and below bright content; existed already with fbcon in rescue Linux.
Ruled out: panel identity (DSI ID read DA=00 DB=80 DC=00 → Novatek NT35523; Orise A1 empty — OTM1287A attempt gave black screen),
init table (ours == vendor "old" table, BOE_HD_LCM=0 selects old), VRF18_1 = 1.8 V, MIPI TX address (DISP_REG_MIPI = 0x14017000),
DSI regs (4 lanes, RGB888 WC 2400, porches, HS timings within spec, PLL 415.6 Mbps), BURST vs SYNC_PULSE (same), A12 higher clock (worse).
Current hypothesis: vendor DSI_set_cmdq_V2 sends cmd >= 0xB0 as GENERIC packets (0x29/0x23/0x13), we sent DCS → A16/A17 send
generic for >= 0xB0 (92 of 93 cmds). NOT yet verified on screen (user away). DSI readback of B1 returns 1 byte 00 regardless —
mtk_dsi reads need max-return-packet-size handling before readback can verify. Boot currently has A17 (A16 + readback probe).
