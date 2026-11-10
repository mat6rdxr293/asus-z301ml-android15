#!/usr/bin/env python3
"""PASSIVE ASUS Z301ML USB watcher: 90 polls / 180 s. NO handshake or reset."""
import datetime,json,re,subprocess,time,sys
from pathlib import Path
p=Path("/Users/matveysazhnov/ASUS-Z301ML-port/mainline/recovery-readcheck")
log=p/"usb-passive-boot-recovery-test.log"
jsonl=p/"usb-passive-boot-recovery-test.jsonl"
if log.exists() or jsonl.exists():
    sys.exit("Refusing to overwrite USB logs: "+str(log))
def capture(cmd,timeout=1.4):
    try:
        r=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
        return r.stdout,r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT",124
    except Exception as e:
        return repr(e),125
def devices(text):
    # IORegistry -l: one USB node usually has both idVendor and idProduct.
    out=[]
    for block in re.split(r'(?m)^\s*(?:\+-o|[| ]+\+-o) ',text):
        vm=re.findall(r'"idVendor"\s*=\s*(\d+)',block)
        pm=re.findall(r'"idProduct"\s*=\s*(\d+)',block)
        if vm and pm:out.append("%04x:%04x"%(int(vm[-1]),int(pm[-1])))
    if not out:
        vm=re.findall(r'"idVendor"\s*=\s*(\d+)',text)
        pm=re.findall(r'"idProduct"\s*=\s*(\d+)',text)
        out=["%04x:%04x"%(int(v),int(q)) for v,q in zip(vm,pm)]
    return sorted(set(out))
def event(message):
    msg=datetime.datetime.now().astimezone().isoformat(timespec="seconds")+" "+message
    print(msg,flush=True)
    with log.open("a") as f:f.write(msg+"\n")
t0=time.monotonic()
event("START passive 180s / 90 samples / interval 2s; no MTKClient commands")
prev=None
for i in range(90):
    t=time.monotonic()
    usb,urc=capture(["ioreg","-p","IOUSB","-l","-w0"])
    adb,arc=capture(["adb","devices","-l"])
    fast,frc=capture(["fastboot","devices"])
    pairs=devices(usb)
    adb_list=[x.strip() for x in adb.splitlines()[1:] if x.strip()]
    fast_list=[x.strip() for x in fast.splitlines() if x.strip()]
    st=(tuple(pairs),tuple(adb_list),tuple(fast_list),urc,arc,frc)
    row={"sample":i+1,"time":datetime.datetime.now().astimezone().isoformat(),"USB":pairs,"ADB":adb_list,"FASTBOOT":fast_list,"rc":[urc,arc,frc]}
    with jsonl.open("a") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    if st!=prev:
        event(f"CHANGE #{i+1}: USB={pairs} ADB={adb_list} FASTBOOT={fast_list} rc={[urc,arc,frc]}")
        prev=st
    time.sleep(max(0,2-(time.monotonic()-t)))
event("COMPLETE: 90 samples taken; see JSONL for every sample")
