import ctypes as C, json, sys, time
from pathlib import Path
u=C.CDLL('/opt/homebrew/opt/libusb/lib/libusb-1.0.dylib')
u.libusb_init.argtypes=[C.POINTER(C.c_void_p)];u.libusb_init.restype=C.c_int
u.libusb_open_device_with_vid_pid.argtypes=[C.c_void_p,C.c_uint16,C.c_uint16];u.libusb_open_device_with_vid_pid.restype=C.c_void_p
u.libusb_control_transfer.argtypes=[C.c_void_p,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.POINTER(C.c_ubyte),C.c_uint16,C.c_uint];u.libusb_control_transfer.restype=C.c_int
u.libusb_close.argtypes=[C.c_void_p];u.libusb_exit.argtypes=[C.c_void_p]
u.libusb_error_name.argtypes=[C.c_int];u.libusb_error_name.restype=C.c_char_p
ctx=C.c_void_p(); assert u.libusb_init(C.byref(ctx))==0
h=u.libusb_open_device_with_vid_pid(ctx,0x0525,0xdead)
if not h: u.libusb_exit(ctx); raise SystemExit('Cannot open PiSight USB device')
def read(typ,request,value,index,length):
 b=(C.c_ubyte*length)(); n=u.libusb_control_transfer(h,typ,request,value,index,b,length,2000)
 if n<0: raise RuntimeError(u.libusb_error_name(n).decode())
 return bytes(b[:n])
try:
 header=read(0x80,6,0x0200,0,9); size=int.from_bytes(header[2:4],'little')
 config=read(0x80,6,0x0200,0,size); pos=0; interface=None; unit=None
 while pos+2<=len(config) and config[pos]>=2:
  d=config[pos:pos+config[pos]]
  if d[1]==4: interface=d[2]
  if len(d)>=24 and d[1:3]==b'\x24\x06' and d[4:20]==b'PiSightSettings1':
   unit=d[3]; control=interface; break
  pos+=d[0]
 if unit is None: raise RuntimeError('PiSight settings extension unit absent')
 print('control interface',control,'extension unit',unit)
 payload=read(0xa1,0x81,0x0100,(unit<<8)|control,8)
 if len(payload)!=8 or payload[0]!=1 or not 25<=payload[1]<=75 or payload[4]>2 or payload[5]>1 or payload[6:]!=bytes(2):
  raise RuntimeError('Invalid PiSight settings response')
 if len(sys.argv)>1:
  if sys.argv[1:] not in (['--mic','on'],['--mic','off']): raise RuntimeError('Usage: usb-settings.py [--mic on|off]')
  saved=Path('/private/tmp/pisight-pwm-test/settings-before-isolation.json')
  if not saved.exists(): saved.write_text(json.dumps({'payload_hex':payload.hex()},indent=2)+'\n')
  original=payload
  desired=bytearray(payload); desired[5]=int(sys.argv[2]=='on')
  buf=(C.c_ubyte*8).from_buffer_copy(desired)
  n=u.libusb_control_transfer(h,0x21,0x01,0x0100,(unit<<8)|control,buf,8,5000)
  if n!=8: raise RuntimeError('SET_CUR failed: '+str(n))
  time.sleep(0.5)
  payload=read(0xa1,0x81,0x0100,(unit<<8)|control,8)
  if payload!=desired: raise RuntimeError('Settings not confirmed by PiSight')
  if payload==original:
   print('Readback already had this value; this does not verify persistence')
  else:
   print('PiSight confirmed the settings change; power cycle required for microphone change')
 print('settings payload',payload.hex())
 print(json.dumps({'version':payload[0],'fov':payload[1],'ev_tenths':int.from_bytes(payload[2:4],'little',signed=True),'logo':payload[4],'microphone':payload[5]}))
finally: u.libusb_close(h);u.libusb_exit(ctx)
