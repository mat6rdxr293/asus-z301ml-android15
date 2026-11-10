#!/usr/bin/env python3
"""pack_recovery.py KERNELBLOB OUT_FULL16MiB [cmdline] — Android v0 using stock recovery header, register SHA in flash script."""
import struct,hashlib,sys
stock=open('/Users/matveysazhnov/ASUS-Z301ML-backup/recovery.bin','rb').read(); page=2048
k=open(sys.argv[1],'rb').read(); import os; r=open(os.environ.get('RAMDISK','artifacts/initramfs-gadget-v2.cpio.gz'),'rb').read()
pad=lambda b:b+bytes((-len(b))%page)
h=bytearray(stock[:page]); struct.pack_into('<I',h,8,len(k)); struct.pack_into('<I',h,16,len(r))
cmd=(sys.argv[3] if len(sys.argv)>3 else "bootopt=64S3,32N2,64N2 console=tty0 loglevel=8 ignore_loglevel rdinit=/init clk_ignore_unused pd_ignore_unused regulator_ignore_unused").encode()
h[64:576]=cmd+bytes(512-len(cmd))
s=hashlib.sha1(); s.update(k); s.update(struct.pack('<I',len(k))); s.update(r); s.update(struct.pack('<I',len(r))); s.update(struct.pack('<I',0))
h[576:596]=s.digest(); h[596:608]=bytes(12)
img=bytes(h)+pad(k)+pad(r); full=img+bytes(16777216-len(img))
open(sys.argv[2],'wb').write(full)
H=hashlib.sha256(full).hexdigest(); print('FULL',H)
p='flash_recovery_and_bcb.py'; t=open(p).read()
if H not in t: t=t.replace("    'e6aa7eac","    '%s': '%s',\n    'e6aa7eac"%(H,sys.argv[2].split('/')[-1]),1); open(p,'w').write(t)
