#!/usr/bin/env python3
"""Three-minute sampling: every 2s ioreg USB, adb devices, fastboot devices.
Pure observation: never sends reset/boot/flash commands.
Writes JSONL events + human log, including USB transitions and serial detections.
"""
import subprocess,time,re,datetime,json,sys,signal
from pathlib import Path
out=Path.home()/"ASUS-Z301ML-port/mainline/usb-monitor-180s.log"
events=out.with_suffix(".jsonl")
start=time.monotonic()
N=90
procs={
    "ioreg": ["ioreg","-p","IOUSB","-l","-w0"],
    "adb": ["adb","devices","-l"],
    "fastboot": ["fastboot","devices"],
}
def run(args,limit=1.9):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=limit)
        return p.stdout,p.returncode
    except subprocess.TimeoutExpired:
        return "",124
    except Exception as e:
        return str(e),255
def device_ids(text):
    # Parse the ioreg dump's idVendor, idProduct in same device dictionary,
    # plus coarse product text from the USB registry.
    ids=[]
    for section in text.split("        }"):
        vendor=re.findall(r'"idVendor"\s*=\s*(\d+)',section)
        product=re.findall(r'"idProduct"\s*=\s*(\d+)',section)
        if vendor and product:
            pair=f"{int(vendor[-1]):04x}:{int(product[-1]):04x}"
            ids.append(pair)
    return sorted(set(ids))
def log(s):
    ts=datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    row=f"{ts} {s}"
    print(row,flush=True)
    with out.open("a") as f:f.write(row+"\n")
def record(item):
    with events.open("a") as f:f.write(json.dumps(item,ensure_ascii=False)+"\n")
last=None
log("START: sampling 90 cycles at 2s intervals (~180s), ioreg + adb + fastboot. READ-ONLY")
for i in range(N):
    t=time.monotonic()
    usb,uc=run(procs["ioreg"],1.6)
    adb,ac=run(procs["adb"],1.6)
    fb,fc=run(procs["fastboot"],1.6)
    ids=device_ids(usb)
    adb_devices=[s.strip() for s in adb.splitlines()[1:] if s.strip()]
    fastboot_devices=[s.strip() for s in fb.splitlines() if s.strip()]
    state={"cycle":i+1,"usb":ids,"adb":adb_devices,"fastboot":fastboot_devices,"timeouts":[name for name,rc in (("ioreg",uc),("adb",ac),("fastboot",fc)) if rc==124]}
    record(state)
    key=(tuple(ids),tuple(adb_devices),tuple(fastboot_devices),tuple(state["timeouts"]))
    if key!=last:
        log(f"CHANGED #{i+1}: USB={ids} ADB={adb_devices} FASTBOOT={fastboot_devices} TIMEOUTS={state['timeouts']}")
        last=key
    # Fixed monotonic schedule
    time.sleep(max(0,2-(time.monotonic()-t)))
log(f"DONE: {N} samples; log={out}; events={events}")
