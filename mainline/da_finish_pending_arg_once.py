#!/usr/bin/env python3
"""ASUS Z301ML ONLY: send a single missing uint32 HOME_SCREEN argument to DA.
SAFE SCOPING: 0e8d:2001 device only; one 4-byte BULK OUT transfer.
NO CMD 0xD9, no flash operations, no USB reset, no retries.
Run only after prior MTKClient FINISH bug may have left the DA expecting mode.
"""
import os,sys,subprocess,time
if os.geteuid()!=0:sys.exit("sudo/root required to access MTK USB device")
check=subprocess.run(['ioreg','-p','IOUSB','-l','-w0'],capture_output=True,text=True,timeout=8).stdout
if ('"idVendor" = 3725' not in check or '"idProduct" = 8193' not in check):
    sys.exit("STOP: Z301ML is not in Legacy DA 0e8d:2001")
import usb.core,usb.util
dev=usb.core.find(idVendor=0x0e8d,idProduct=0x2001)
if not dev:sys.exit("STOP: DA USB not accessible; no operation attempted")
cfg=dev.get_active_configuration()
if cfg.bNumInterfaces not in (1,2):
    sys.exit("STOP: unexpected USB interface count "+str(cfg.bNumInterfaces))
# MTKClient selects interface 0 when default_ids interface=-1.
intf=cfg[(0,0)]
outs=[e for e in intf if usb.util.endpoint_direction(e.bEndpointAddress)==usb.util.ENDPOINT_OUT
      and usb.util.endpoint_type(e.bmAttributes)==usb.util.ENDPOINT_TYPE_BULK]
ins=[e for e in intf if usb.util.endpoint_direction(e.bEndpointAddress)==usb.util.ENDPOINT_IN
      and usb.util.endpoint_type(e.bmAttributes)==usb.util.ENDPOINT_TYPE_BULK]
print("Target vendor/product:",hex(dev.idVendor),hex(dev.idProduct),flush=True)
print("USB interface",intf.bInterfaceNumber,"BULK OUT",[hex(x.bEndpointAddress) for x in outs],
      "BULK IN",[hex(x.bEndpointAddress) for x in ins],flush=True)
if len(outs)!=1 or len(ins)!=1:sys.exit("STOP: unexpected USB endpoints")
usb.util.claim_interface(dev,intf.bInterfaceNumber)
try:
    mode=b'\x00\x00\x00\x01'
    print("Sending ONE raw 4-byte HOME_SCREEN argument: 00000001, no eMMC commands.",flush=True)
    wrote=outs[0].write(mode,timeout=1200)
    print("BULK OUT result",wrote,"bytes",flush=True)
    if wrote!=4:sys.exit("STOP: 4-byte write incomplete")
    try:
        ack=bytes(ins[0].read(1,timeout=1400))
        print("DA reply:",ack.hex(),flush=True)
    except usb.core.USBError as e:
        print("No ACK (possible disconnect or protocol desync):",str(e),flush=True)
finally:
    usb.util.dispose_resources(dev)
print("Raw pending FINISH argument attempt complete; monitor re-enumeration.",flush=True)
