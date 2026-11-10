import subprocess,re,time,glob,serial,threading,http.server,socketserver,os
d=os.path.abspath('testframes')
hp=subprocess.run(['networksetup','-listallhardwareports'],capture_output=True,text=True).stdout
dev=re.search(r'Hardware Port: Z301ML[^\n]*\nDevice: (\S+)',hp).group(1)
ip=re.search(r'inet (169\.254\.\d+\.\d+)',subprocess.run(['/sbin/ifconfig',dev],capture_output=True,text=True).stdout).group(1)
class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(s,*a,**k): super().__init__(*a,directory=d,**k)
    def log_message(s,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer((ip,8766),Q); threading.Thread(target=srv.serve_forever,daemon=True).start()
s=serial.Serial(glob.glob('/dev/cu.usbmodem[0-9]*')[0],115200,timeout=0.3)
def run(c,to=60):
    s.write(b'\n'); time.sleep(0.2); s.reset_input_buffer(); s.write((c+'; echo __DONE__\n').encode()); o=b''; t=time.time()
    while time.time()-t<to:
        o+=s.read(65536)
        if o.count(b'__DONE__')>=2: break
    return o.decode('latin1')
print(run(f'ifconfig usb0 169.254.77.2 netmask 255.255.0.0 up; cd /tmp; for f in red green blue bars; do wget -q -O $f.raw http://{ip}:8766/$f.raw; done; ls -l /tmp/*.raw',120)[-400:])
print('SHOW'); print(run('for f in red green blue bars; do cat /tmp/$f.raw > /dev/fb1; sleep 4; done; echo 1023 > /sys/class/backlight/backlight/brightness; sleep 3; echo 30 > /sys/class/backlight/backlight/brightness; sleep 3; echo 600 > /sys/class/backlight/backlight/brightness',60)[-200:])
srv.shutdown()
