#!/usr/bin/env python3
"""Offline ASUS Z301ML Android v0 boot image repacker for EARLY DIAGNOSTIC Linux.
NO USB/ADB use, NO device writes. Generated file is UNSIGNED and NOT FLASH-READY.
"""
import argparse
import hashlib
import struct
import zlib
from pathlib import Path

MAX_BOOT_BYTES = 16 * 1024 * 1024
STOCK = Path.home() / "ASUS-Z301ML-recovery/stock-boot.img"

def page_pad(data, page):
    return data + bytes((-len(data)) % page)

def android_sha1(kernel, ramdisk):
    h = hashlib.sha1()
    h.update(kernel)
    h.update(struct.pack("<I",len(kernel)))
    h.update(ramdisk)
    h.update(struct.pack("<I",len(ramdisk)))
    h.update(struct.pack("<I",0))
    return h.digest()

def build(kernel_path, dtb_path, ramdisk_path, output_path):
    stock = STOCK.read_bytes()
    fields = struct.unpack_from("<10I", stock, 8)
    ksize, _, rsize, _, second_size, _, _, page, dt_size, unused = fields
    assert stock[:8] == b"ANDROID!"
    assert page == 2048 and second_size == 0 and dt_size == 0
    assert unused == 0x0E000125
    stock_kernel = stock[page:page + ksize]
    rstart = page + len(page_pad(stock_kernel, page))
    stock_ramdisk = stock[rstart:rstart + rsize]
    assert android_sha1(stock_kernel,stock_ramdisk) == stock[576:596], "Factory boot ID inconsistent"

    compressed = kernel_path.read_bytes()
    assert compressed.startswith(b"\x1f\x8b\x08")
    obj = zlib.decompressobj(31)
    decompressed = obj.decompress(compressed) + obj.flush()
    assert decompressed.startswith(b"MZ") or decompressed[56:64].startswith(b"ARM"), "Unexpected ARM64 kernel header"
    assert not obj.unused_data, "Kernel already contains trailing data"
    dtb = dtb_path.read_bytes()
    assert dtb[:4] == bytes.fromhex("d00dfeed")
    assert struct.unpack_from(">I", dtb, 4)[0] == len(dtb)
    kernel = compressed + dtb
    ramdisk = ramdisk_path.read_bytes()
    assert zlib.decompress(ramdisk,31).startswith(b"070701"), "Ramdisk must be gzip-compressed newc initramfs"

    header = bytearray(stock[:page])
    struct.pack_into("<I", header, 8, len(kernel))
    struct.pack_into("<I", header, 16, len(ramdisk))
    header[576:596] = android_sha1(kernel, ramdisk)
    header[596:608] = bytes(12)
    new_cmdline = b"bootopt=64S3,32N2,64N2 console=ttyS0,921600n8 loglevel=8 ignore_loglevel rdinit=/init"
    assert len(new_cmdline) < 512
    header[64:576] = new_cmdline + bytes(512 - len(new_cmdline))
    new = bytes(header) + page_pad(kernel, page) + page_pad(ramdisk, page)
    assert len(new) <= MAX_BOOT_BYTES, f"Image {len(new)} exceeds {MAX_BOOT_BYTES} bytes boot partition"
    assert new[page:page+len(kernel)] == kernel
    rstart2 = page + len(page_pad(kernel, page))
    assert new[rstart2:rstart2+len(ramdisk)] == ramdisk
    assert android_sha1(kernel, ramdisk) == new[576:596]
    assert not output_path.exists(), f"{output_path} exists; refusing overwrite"
    output_path.write_bytes(new)
    print("ANDROID BOOT V0 VERIFIED. STOCK SHA1 VERIFIED.")
    print("NEW ARM64 KERNEL:", len(compressed), "bytes")
    print("APPENDED ASUS DTB:", len(dtb), "bytes")
    print("STATIC BUSYBOX DIAGNOSTIC INITRAMFS:", len(ramdisk), "bytes")
    print("BOOTSCRIPT: /init, console ttyS0")
    print("NEW IMAGE:", output_path)
    print("NEW SIZE:", len(new), "bytes; boot maximum:", MAX_BOOT_BYTES, "; margin:", MAX_BOOT_BYTES-len(new))
    print("SHA256:", hashlib.sha256(new).hexdigest())
    print("CAUTION: UNSIGNED, UNTESTED, EXPERIMENTAL. NO DEVICE WRITE OCCURRED.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--kernel",required=True,type=Path)
    p.add_argument("--dtb",required=True,type=Path)
    p.add_argument("--ramdisk",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    x = p.parse_args()
    build(x.kernel,x.dtb,x.ramdisk,x.output)
