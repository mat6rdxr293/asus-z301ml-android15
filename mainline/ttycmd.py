import serial,sys,time
s=serial.Serial('/dev/cu.usbmodem1101',115200,timeout=0.5)
def run(cmd,wait=1.5):
    s.reset_input_buffer(); s.write((cmd+'\n').encode()); time.sleep(wait)
    out=b''
    while True:
        b=s.read(65536)
        if not b: break
        out+=b
    return out.decode('latin1')
print(run('',1))
for c in sys.argv[1:]:
    print('### '+c); print(run(c, 3 if 'dmesg' in c else 1.5))
