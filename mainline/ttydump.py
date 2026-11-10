import serial,time,glob,sys
p=glob.glob('/dev/cu.usbmodem[0-9]*')
if not p: print('no port'); sys.exit()
s=serial.Serial(p[0],115200,timeout=0.3)
s.write(b'\n'); time.sleep(0.3); s.reset_input_buffer()
s.write(b'dmesg; cat /proc/cmdline; ls /sys/class/udc; cat /proc/partitions; echo __END__\n')
out=b''; t=time.time()
try:
    while time.time()-t<12:
        b=s.read(65536)
        if b: out+=b
        if b'__END__\n' in out[-200:] and out.count(b'__END__')>=2: break
except Exception as e: print('ERR',e)
open('/Users/matveysazhnov/ASUS-Z301ML-port/mainline/crashlogs/linux7-v8-dmesg-usb.txt','wb').write(out)
print(len(out))
