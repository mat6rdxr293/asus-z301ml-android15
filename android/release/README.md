# Android 15 для ASUS ZenPad 10 Z301ML (P00L)

Неофициальная прошивка: Android 15 (AOSP GSI) на ядре Linux 7.0 для **ASUS ZenPad 10 Z301ML (P00L,
MediaTek MT8735)**. Только для этой модели. Работа экспериментальная — ставите на свой риск.

## Что работает

- Экран, тачскрин, кнопка питания, подсветка
- Графика на GPU (Mali-T720, Panfrost / Mesa, OpenGL ES 2.0)
- Wi-Fi (2.4 и 5 ГГц), Bluetooth (спаривание, профили A2DP/HID/PAN/OPP)
- Звук через динамик, видео (YouTube в браузере)
- Аккумулятор, частоты процессора, термозащита

## Что не работает / известные проблемы

- Сон (планшет не засыпает — батарея садится быстрее), наушники (звук всегда в динамике), микрофон
- Камеры, датчики (акселерометр, свет), модем/LTE, GPS
- Кнопки громкости, Vulkan (только программный), блюр в интерфейсе
- При загрузке может появиться окно «Внутренняя ошибка Android» — его можно закрыть
- На некоторых экранах со временем появляются вертикальные полосы — помогает выключить/включить экран

## Что нужно

- Компьютер с Windows, Linux или macOS и Python 3.9+
- [mtkclient](https://github.com/bkerler/mtkclient) — установить по его инструкции
  (на Windows обязательно драйвер UsbDk, см. README-WINDOWS.md в mtkclient)
- USB-кабель и заряженный планшет (> 50 %)
- 10 ГБ свободного места для резервной копии

## Установка

Режим BROM: **выключите планшет, отключите кабель, зажмите «Громкость −» и подключите кабель**.
Отпустите кнопку, когда mtkclient подключится. Для каждого шага ниже нужно войти в BROM заново.

1. **Резервная копия** (ничего не записывает, 30–60 минут):
   ```
   python flash/z301ml_flash.py --mtk ПУТЬ/К/mtkclient/mtk.py backup
   ```
   Появится папка `backup/`. **Скопируйте её в надёжное место** — там IMEI, MAC-адреса и калибровки
   вашего планшета. Никому её не передавайте.

2. **Установка Android 15** (стирает все данные на планшете):
   ```
   python flash/z301ml_flash.py --mtk ПУТЬ/К/mtkclient/mtk.py install
   ```
   Скрипт проверит, что это именно Z301ML с правильной разметкой, и только тогда начнёт запись.
   Первая загрузка — 2–4 минуты.

## Возврат на стоковую прошивку

```
python flash/z301ml_flash.py --mtk ПУТЬ/К/mtkclient/mtk.py restore
```
Записывает обратно ваши `boot`, `system`, `cache`, `para` из `backup/` и стирает данные.

## Что меняется на планшете

Пишутся только `boot` (ядро), `system` (Android 15 GSI), `cache` (используется как раздел vendor),
первый сектор `para` (сброс команды загрузчика) и начало `userdata` (форматируется при первой загрузке).
Загрузчики (preloader, lk), `nvram`, `nvdata`, `persist`, `recovery` не трогаются.

## Исходники

Ядро, драйверы и конфигурация vendor — в репозитории проекта. Образ `system.img` — AOSP GSI
`aosp_arm64` BP11.241210.004 (Google). В `vendor.img` есть бинарные прошивки Wi-Fi/Bluetooth MediaTek
из стоковой прошивки и компоненты Cuttlefish (AOSP).

---

## English (short)

Unofficial Android 15 (AOSP GSI) on Linux 7.0 for the ASUS ZenPad 10 Z301ML (P00L, MT8735) only.
Needs [mtkclient](https://github.com/bkerler/mtkclient). Enter BROM: tablet off, hold Volume Down, plug USB.
`python flash/z301ml_flash.py --mtk path/to/mtk.py backup` (read-only, keep the backup safe), then
`... install` (wipes the tablet). `... restore` puts stock boot/system/cache/para back.
Works: display, touch, GPU (Panfrost), Wi-Fi, Bluetooth, speaker. Not working: sleep, headphones, mic,
cameras, sensors, modem, GPS.
