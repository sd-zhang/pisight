#!/usr/bin/env python3
"""Read PiSight snapshots over existing UVC XU selector 2. No drive access.

Run after capture; snapshotting/log transfer can consume CPU while requested.
Requires the diagnostic XU firmware, not the earlier settings-only firmware.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
from pathlib import Path
import struct

MAX_SIZE=4*1024*1024
STATUS={1:'no snapshot',2:'target file unavailable/read failed',3:'offset out of range',4:'invalid request or stale snapshot',5:'snapshot exceeds 4 MiB',6:'target allocation failed'}

def command(operation,source=0,generation=0,offset=0):
    return struct.pack('<BBBBII',1,operation,source,0,generation,offset)+bytes(48)

def fetch_snapshot(exchange,source=0):
    """exchange(direction, request, data-or-IN-length) supplies USB transport."""
    def send(data):
        if exchange('out',1,data)!=60:raise ValueError('Short diagnostic command transfer')
    if exchange('in',0x85,2)!=b'\x3c\0':raise ValueError('Unsupported diagnostic control size')
    try:
        send(command(1,source))
        result=bytearray();generation=None;total=None
        while True:
            packet=exchange('in',0x81,60)
            if len(packet)!=60:raise ValueError('Short diagnostic response')
            version,status,count,flags,gen,size,offset=struct.unpack('<BBBBIII',packet[:16])
            if version!=1:raise ValueError('Unsupported diagnostic version')
            if status:raise RuntimeError(STATUS.get(status,'Unknown target status '+str(status)))
            if generation is None:generation,total=gen,size
            if not gen or gen!=generation or size!=total or size>MAX_SIZE:
                raise ValueError('Changed or invalid snapshot generation/size')
            if offset!=len(result) or offset>size or count!=min(44,size-offset):
                raise ValueError('Invalid diagnostic offset or payload length')
            if flags!=int(offset+count==size) or any(packet[16+count:]):
                raise ValueError('Invalid diagnostic EOF/padding')
            result.extend(packet[16:16+count])
            if flags:return bytes(result)
            send(command(2,generation=generation,offset=len(result)))
    finally:
        try:send(command(3))
        except Exception:pass  # Preserve the original transfer/validation error.

class UsbReader:
    def __init__(self):
        self.lib=C.CDLL('/opt/homebrew/opt/libusb/lib/libusb-1.0.dylib')
        u=self.lib
        u.libusb_init.argtypes=[C.POINTER(C.c_void_p)];u.libusb_init.restype=C.c_int
        u.libusb_open_device_with_vid_pid.argtypes=[C.c_void_p,C.c_uint16,C.c_uint16];u.libusb_open_device_with_vid_pid.restype=C.c_void_p
        u.libusb_control_transfer.argtypes=[C.c_void_p,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.POINTER(C.c_ubyte),C.c_uint16,C.c_uint];u.libusb_control_transfer.restype=C.c_int
        u.libusb_close.argtypes=[C.c_void_p];u.libusb_exit.argtypes=[C.c_void_p]
        u.libusb_error_name.argtypes=[C.c_int];u.libusb_error_name.restype=C.c_char_p
        self.ctx=C.c_void_p();self.handle=None
        rc=u.libusb_init(C.byref(self.ctx))
        if rc<0:raise RuntimeError('libusb init failed: '+str(rc))
        try:
            self.handle=u.libusb_open_device_with_vid_pid(self.ctx,0x0525,0xdead)
            if not self.handle:raise RuntimeError('PiSight USB device unavailable')
            header=self.transfer(0x80,6,0x0200,0,9)
            if len(header)!=9:raise ValueError('Short configuration header')
            size=int.from_bytes(header[2:4],'little')
            config=self.transfer(0x80,6,0x0200,0,size)
            if len(config)!=size:raise ValueError('Short configuration descriptor')
            interface=None;pos=0
            while pos+2<=len(config):
                length=config[pos]
                if length<2 or pos+length>len(config):raise ValueError('Malformed USB descriptor')
                d=config[pos:pos+length]
                if d[1]==4 and len(d)>=9:interface=d[2]
                if d[1:3]==b'\x24\x06' and len(d)>=24 and d[4:20]==b'PiSightSettings1':
                    pins=d[21];control_size_at=22+pins
                    if interface is None or control_size_at>=len(d):raise ValueError('Malformed PiSight XU')
                    size=d[control_size_at];controls=d[control_size_at+1:control_size_at+1+size]
                    if not controls or not controls[0]&2:raise RuntimeError('This firmware has settings only; USB diagnostic readback is absent')
                    self.index=(d[3]<<8)|interface
                    return
                pos+=length
            raise RuntimeError('PiSight extension unit absent')
        except Exception:
            self.close();raise
    def transfer(self,typ,request,value,index,payload):
        incoming=bool(typ&0x80)
        length=payload if incoming else len(payload)
        buf=(C.c_ubyte*length)() if incoming else (C.c_ubyte*length).from_buffer_copy(payload)
        n=self.lib.libusb_control_transfer(self.handle,typ,request,value,index,buf,length,5000)
        if n<0:raise RuntimeError(self.lib.libusb_error_name(n).decode())
        return bytes(buf[:n]) if incoming else n
    def exchange(self,direction,request,payload):
        return self.transfer(0xa1 if direction=='in' else 0x21,request,0x0200,self.index,payload)
    def close(self):
        if self.handle:self.lib.libusb_close(self.handle);self.handle=None
        if self.ctx:self.lib.libusb_exit(self.ctx);self.ctx=None

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=['log','usb'],default='log')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=args.output or Path('diagnostics')/('usb-'+args.source+'-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.log')
    if output.exists():raise FileExistsError(output)
    usb=UsbReader()
    try:data=fetch_snapshot(usb.exchange,int(args.source=='usb'))
    finally:usb.close()
    # Publish only the fully validated response; never leave a successful-looking partial log.
    with output.open('xb') as f:f.write(data)
    print(f'{output}: {len(data)} bytes; SHA256 {hashlib.sha256(data).hexdigest()}')

if __name__=='__main__':main()
