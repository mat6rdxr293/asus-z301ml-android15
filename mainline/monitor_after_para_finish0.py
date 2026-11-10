#!/usr/bin/env python3
"""ASUS P00L: 120-second USB/ADB/Fastboot monitor after guarded DA exit.
Runs BEFORE sending FINISH, records changes every 2s; no eMMC writes.
"""
import subprocess,time,datetime,re,json
from pathlib import Path
R=Path("/Users/matveysazhnov/ASUS-Z301ML-port/mainline/recovery-readcheck")
LOG=R/"usb-after-para-finish0-120s.log"
EVENTS=R/"usb-after-para-finish0-120s.jsonl"
if LOG.exists() or EVENTS.exists():raise SystemExit("Monitor logs exist; no overwrite")
def run(a,timeout=1.6):
 try:
  o=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
  return o.stdout.strip(),o.returncode
 except subprocess.TimeoutExpired:return "",124
 except Exception as e:return repr(e),255
def usb_pairs(out):
 # IORegistry device nodes include idVendor/idProduct as separate dict entries
 found=[]
 for chunk in out.split('+-o'):
  v=re.findall(r'"idVendor"\s*=\s*(\d+)',chunk)
  p=re.findall(r'"idProduct"\s*=\s*(\d+)',chunk)
  if v and p:found.append(f"{int(v[-1]):04x}:{int(p[-1]):04x}")
 return sorted(set(found))
def printlog(s):
 msg=datetime.datetime.now().astimezone().isoformat(timespec="seconds")+' '+s
 print(msg,flush=True)
 with LOG.open('a') as f:f.write(msg+'\n')
known=None
adb_reboot_sent=False
printlog("START 120s: ioreg USB + adb devices -l + fastboot devices, 2s intervals")
t0=time.monotonic()
for i in range(60):
 t=time.monotonic()
 usb,eu=run(["ioreg","-p","IOUSB","-l","-w0"])
 adb,ea=run(["adb","devices","-l"])
 fast,ef=run(["fastboot","devices"])
 p=usb_pairs(usb)
 adbdevices=[x for x in adb.splitlines()[1:] if x.strip()]
 fastdevices=fast.splitlines()
 event={"n":i+1,"time":datetime.datetime.now().isoformat(),"USB":p,"ADB":adbdevices,"FASTBOOT":fastdevices,"exit_codes":[eu,ea,ef]}
 with EVENTS.open('a') as f:f.write(json.dumps(event)+'\n')
 state=(tuple(p),tuple(adbdevices),tuple(fastdevices),eu,ea,ef)
 if state!=known:
  printlog(f"CHANGED #{i+1} USB={p} ADB={adbdevices} FASTBOOT={fastdevices} rc={[eu,ea,ef]}")
  known=state
 if adbdevices and not adb_reboot_sent:
  if any(' device ' in (' '+a+' ') or '\tdevice' in a for a in adbdevices):
   model,_=run(["adb","shell","getprop","ro.product.model"],timeout=5)
   kernel,_=run(["adb","shell","uname","-r"],timeout=5)
   cmdline,_=run(["adb","shell","cat","/proc/cmdline"],timeout=5)
   printlog(f"ADB RUNNING model={model!r}, uname={kernel!r}, cmdline={cmdline[:150]!r}")
   if ('P00L' in model or 'ASUS' in model or 'ZenPad' in model) and kernel and '3.18' not in kernel:
    printlog("ADB Android on expected model: attempting reboot recovery")
    result,code=run(["adb","reboot","recovery"],timeout=7)
    printlog(f"ADB reboot recovery: rc={code}, output={result}")
    adb_reboot_sent=True
 time.sleep(max(0,2-(time.monotonic()-t)))
printlog("END: 60 samples over ~120 s; no partition writes")
