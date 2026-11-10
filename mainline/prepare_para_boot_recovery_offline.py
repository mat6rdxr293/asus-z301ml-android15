#!/usr/bin/env python3
"""OFFLINE only. Construct a strictly 512-byte Android BCB command sector from
a verified read-only backup of Z301ML's 512 KiB 'para' partition.
No USB access, no eMMC writes. A separate guarded script must verify live
device identity, GPT layout, backup and live prewrite bytes before any write.
"""
from pathlib import Path
import hashlib,sys
W=Path("/Users/matveysazhnov/ASUS-Z301ML-port/mainline/recovery-readcheck")
PARA=W/"live-para-backup-1800.bin"
RECO=W/"live-recovery-1800.bin"
CMD=W/"para-boot-recovery-sector-512-PREPARED-NOT-FLASHED.bin"
EXPECTED="e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2"
def sha(data):return hashlib.sha256(data).hexdigest()
def check(x,msg):
 if not x:sys.exit("ABORT: "+msg)
check(PARA.is_file(),"para backup not yet captured")
check(RECO.is_file(),"recovery readback not yet captured")
p=PARA.read_bytes();r=RECO.read_bytes()
check(len(p)==524288,"para partition must be exactly 0x80000")
check(len(r)==16777216 and sha(r)==EXPECTED,"live recovery does not match experimental 3.18.35 kernel; STOP")
check(not CMD.exists(),"proposed sector already exists; never overwrite")
print("PARA original SHA256:",sha(p))
print("PARA first 64 bytes (hex):",p[:64].hex())
print("PARA BCB command field repr:",repr(p[:32]))
# Avoid corrupting an OEM-specific header at start of para.
cmdfield=p[:32]
known={b"",b"boot-recovery",b"bootonce-bootloader",b"boot-bootloader"}
prefix=cmdfield.rstrip(b'\x00')
if prefix not in known and cmdfield != b'\xff'*32:
 sys.exit("ABORT: para[0:32] contains unexpected bytes. Need LK verification before patch.")
new=bytearray(p[:512])
new[:32]=b"boot-recovery"+bytes(32-len(b"boot-recovery"))
check(new[32:]==p[32:512],"bytes outside 32-byte command field modified")
check(new[:32].split(b'\0')[0]==b"boot-recovery","bad command")
CMD.write_bytes(new)
print("PREPARED ONLY:",CMD)
print("SECTOR_SIZE",CMD.stat().st_size,"SHA256",sha(new))
print("Changed positions:",[i for i in range(512) if p[i]!=new[i]])
print("NO DEVICE WRITE; original para backed up in full.")
