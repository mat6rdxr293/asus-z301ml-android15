import serial,time,glob,sys
p=glob.glob('/dev/cu.usbmodem[0-9]*'); s=serial.Serial(p[0],115200,timeout=0.3)
s.write(b'\n'); time.sleep(0.3); s.reset_input_buffer()
s.write((sys.argv[1]+'; echo __END__\n').encode())
out=b''; t=time.time()
while time.time()-t<float(sys.argv[2] if len(sys.argv)>2 else 5):
    b=s.read(65536); out+=b
    if out.count(b'__END__')>=2: break
print(out.decode('latin1'))
