#!/usr/bin/env python3
"""Reset ONLY USB transport 0e8d:2001 after DA finish was ACKed.
USB bus reset does not write eMMC or modify partitions.
"""
import os,sys,subprocess
from pathlib import Path
if os.geteuid()!=0:sys.exit("sudo required")
log=Path("/Users/matveysazhnov/ASUS-Z301ML-port/mainline/recovery-readcheck/da-pending-arg-second.log")
if not log.is_file() or "DA reply: 5a" not in log.read_text():
    sys.exit("STOP: confirmed 0x5A ACK missing from DA finish log")
r=subprocess.run(["ioreg","-p","IOUSB","-l","-w0"],capture_output=True,text=True,timeout=6)
if '"idVendor" = 3725' not in r.stdout or '"idProduct" = 8193' not in r.stdout:
    sys.exit("STOP: expected 0e8d:2001 USB DA not connected")
import usb.core,usb.util
dev=usb.core.find(idVendor=0x0e8d,idProduct=0x2001)
if not dev:sys.exit("STOP: target USB DA not accessible")
print("DA mode HOME_SCREEN=1 was accepted with ACK 0x5A. Applying one USB bus reset.",flush=True)
try:
    dev.reset()
    print("USB DEVICE RESET request completed.",flush=True)
except usb.core.USBError as e:
    print("USB DEVICE RESET returned:",str(e),flush=True)
print("Monitor USB re-enumeration and Android/Fastboot externally.",flush=True)
