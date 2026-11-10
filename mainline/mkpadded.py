#!/usr/bin/env python3
"""mkpadded.py INNER_RAW DTB OUT : gzip(INNER + random pad) sized like stock (~7.8 MB gz, 0x11a97e0 decompressed) + DTB.
Stock MTK LK on Z301ML does not jump into kernels whose gzip stream is small (bisected 2026-11-08: S2 vs S3)."""
import sys,gzip,os
STOCK_GZ=7812758; STOCK_DEC=0x11a97e0
inner=open(sys.argv[1],'rb').read(); dtb=open(sys.argv[2],'rb').read()
assert dtb[:4]==bytes.fromhex('d00dfeed')
need_rand=max(0,STOCK_GZ+12000-len(gzip.compress(inner,9,mtime=0)))
body=inner+os.urandom(need_rand)
if len(body)<STOCK_DEC: body+=bytes(STOCK_DEC-len(body))
gz=bytearray(gzip.compress(body,9,mtime=0)); gz[8]=2; gz[9]=3
open(sys.argv[3],'wb').write(bytes(gz)+dtb)
print('inner',len(inner),'decomp',hex(len(body)),'gz',len(gz),'dtb',len(dtb))
