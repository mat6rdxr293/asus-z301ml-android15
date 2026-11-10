#!/usr/bin/env python3
"""ASUS Z301ML boot probe after leaving MTK Legacy DA.
Only authorized ADB reboot recovery, no partition writes.
"""
import subprocess,time,sys,datetime
DEVICE="H6NPFP022437BJH"
def run(args,timeout=5):
    try:
        a=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        return a.returncode,(a.stdout+a.stderr).strip()
    except Exception as e:return -1,str(e)
def log(*a):print(datetime.datetime.now().strftime('%H:%M:%S'),*a,flush=True)
log("Watch USB/ADB after DA shutdown bootmode=1 (HOME_SCREEN)")
start=time.monotonic()
last=""
sent=False
while time.monotonic()-start<240:
    _, devices=run(["adb","devices","-l"],timeout=5)
    if devices!=last:
        log("ADB devices:",repr(devices)[:260]); last=devices
    if f"{DEVICE} device" in devices:
        _, model=run(["adb","-s",DEVICE,"shell","getprop","ro.product.model"],timeout=8)
        _, kernel=run(["adb","-s",DEVICE,"shell","uname","-r"],timeout=8)
        _, done=run(["adb","-s",DEVICE,"shell","getprop","sys.boot_completed"],timeout=8)
        log("Device detected, model",model,"kernel",kernel,"boot_completed",done)
        if not sent and model.strip()=="P00L" and done.strip()=="1":
            log("Android boot confirmed; sending adb reboot recovery")
            code,result=run(["adb","-s",DEVICE,"reboot","recovery"],timeout=15)
            log("adb reboot recovery exit",code,result)
            sent=code==0
            if sent:break
    time.sleep(3)
if not sent:
    log("No successful ADB recovery reboot. Ending probe without any device writes.")
    sys.exit(1)
log("Observing Recovery USB enumeration")
deadline=time.monotonic()+70
while time.monotonic()<deadline:
    _, devices=run(["adb","devices","-l"],timeout=5)
    fast=run(["fastboot","devices"],timeout=4)[1]
    _,usb=run(["ioreg","-p","IOUSB","-l","-w0"],timeout=6)
    found=[]
    for line in usb.splitlines():
        if '"idVendor"' in line or '"idProduct"' in line:
            found.append(line.strip())
    log("Recovery probe: ADB=",repr(devices)[:190],"fastboot=",fast[:90],"USB IDs=",str(found[-12:])[:220])
    time.sleep(8)
log("Probe finished.")
