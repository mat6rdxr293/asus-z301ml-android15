#!/usr/bin/env python3
"""flash_from_linux.py IMAGE [--no-reboot]
Write a 16 MiB recovery image from the running mainline Linux (USB ACM shell + ECM net):
Mac HTTP (link-local) -> wget -> sha256 -> dd to the GPT partition named 'recovery' -> readback sha256 -> reboot.
No BROM/DA needed. Refuses unless PARTNAME of the target is 'recovery' and size is 16 MiB."""
import sys,os,glob,time,serial,hashlib,subprocess,http.server,threading,socketserver,re
img=os.path.abspath(sys.argv[1]); data=open(img,'rb').read()
assert len(data)==16*1024*1024 and data[:8]==b'ANDROID!', 'bad image'
H=hashlib.sha256(data).hexdigest()
mac_ip=None
for _ in range(60):
    hp=subprocess.run(['networksetup','-listallhardwareports'],capture_output=True,text=True).stdout
    m=re.search(r'Hardware Port: Z301ML[^\n]*\nDevice: (\S+)',hp)
    if m:
        o=subprocess.run(['/sbin/ifconfig',m.group(1)],capture_output=True,text=True).stdout
        mm=re.search(r'inet (169\.254\.\d+\.\d+)',o)
        if mm: mac_ip=mm.group(1)
    if mac_ip: break
    time.sleep(2)
assert mac_ip, 'no link-local on ECM iface (02:00:00:00:aa:02)'
d=os.path.dirname(img); name=os.path.basename(img); PORT=8765
class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(s,*a,**k): super().__init__(*a,directory=d,**k)
    def log_message(s,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer((mac_ip,PORT),Q); threading.Thread(target=srv.serve_forever,daemon=True).start()
p=glob.glob('/dev/cu.usbmodem[0-9]*')[0]; s=serial.Serial(p,115200,timeout=0.3)
def run(cmd,to=60,mark='__DONE__'):
    s.write(b'\n'); time.sleep(0.2); s.reset_input_buffer()
    s.write((cmd+f'; echo {mark}\n').encode()); out=b''; t=time.time()
    while time.time()-t<to:
        out+=s.read(65536)
        if out.count(mark.encode())>=2: break
    return out.decode('latin1')
o=run('ifconfig usb0 169.254.77.2 netmask 255.255.0.0 up; for b in /sys/class/block/mmcblk*p*; do grep -q "^PARTNAME=recovery$" $b/uevent && echo RECDEV=$(basename $b); done'); print(o)
m=re.search(r'RECDEV=(mmcblk\d+p\d+)',o); assert m, 'recovery partition not found'; DEV='/dev/'+m.group(1); print('target',DEV)
o=run(f'grep -q PARTNAME=recovery /sys/class/block/{DEV[5:]}/uevent && [ $(blockdev --getsize64 {DEV}) = 16777216 ] && echo TARGET_OK')
assert 'TARGET_OK\r' in o or 'TARGET_OK\n' in o, o
o=run(f'rm -f /tmp/r.img; wget -q -O /tmp/r.img http://{mac_ip}:{PORT}/{name} && sha256sum /tmp/r.img',120); print(o[-200:])
assert H in o, 'download sha mismatch'
o=run(f'dd if=/tmp/r.img of={DEV} bs=1M conv=fsync 2>&1; sync; dd if={DEV} bs=1M count=16 2>/dev/null | sha256sum',120); print(o[-300:])
assert o.count(H)>=1 and 'records out' in o, 'readback mismatch'
print('FLASHED + VERIFIED', name, H[:16])
if '--no-reboot' not in sys.argv:
    s.write(b'sync; reboot -f\n'); time.sleep(1); print('reboot sent')
srv.shutdown()
