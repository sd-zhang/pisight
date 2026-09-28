from pathlib import Path
import subprocess,sys,tempfile
root=Path(sys.argv[1]); src=(root/'lib/uvc.c').read_text()
start=src.index('static void\nuvc_events_process_control('); end=src.index('\nstatic void\nuvc_events_process_streaming',start)
prefix='''#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define UVC_SET_CUR 1
#define UVC_GET_CUR 129
#define UVC_GET_MIN 130
#define UVC_GET_MAX 131
#define UVC_GET_RES 132
#define UVC_GET_LEN 133
#define UVC_GET_INFO 134
#define UVC_GET_DEF 135
#define UVC_CT_ZOOM_ABSOLUTE_CONTROL 11
#define UVC_PU_BRIGHTNESS_CONTROL 2
'''
if (root/'lib/pisight-diagnostic.h').exists(): prefix+='#include "pisight-diagnostic.h"\n'
else: prefix+='struct pisight_diagnostic {int unused;};\n'
api=(root/'include/linux/usb/g_uvc.h').read_text()
api=api[api.index('struct uvc_request_data {'):api.index('struct uvc_event {')]
prefix+='#include "pisight-controls.h"\n'
prefix+=api.replace('__s32','int32_t').replace('__u8','uint8_t')
prefix+='''
struct uvc_device {int xu_unit,control_entity,control,fov,saved_ev,logo_mode,microphone,zoom,brightness; struct pisight_diagnostic diagnostic; struct pisight_controls settings;};
'''
setup_start=src.find('static int uvc_is_diagnostic(')
if setup_start<0:setup_start=src.index('static void\nuvc_events_process_setup(')
setup_end=src.index('static int uvc_store_settings',setup_start)
setup=src[setup_start:setup_end]
prefix+='''
#define USB_RECIP_MASK 31
#define USB_RECIP_INTERFACE 1
#define USB_TYPE_MASK 96
#define USB_TYPE_STANDARD 0
#define USB_TYPE_CLASS 32
#define UVC_STRING_CONTROL_IDX 0
#define uvc_log(...) ((void)0)
struct usb_ctrlrequest {uint8_t bRequestType,bRequest;uint16_t wValue,wIndex,wLength;};
static int fallback;
static void uvc_events_process_standard(struct uvc_device *d,const struct usb_ctrlrequest *c,struct uvc_request_data *r){(void)d;(void)c;(void)r;fallback++;}
static void uvc_events_process_class(struct uvc_device *d,const struct usb_ctrlrequest *c,struct uvc_request_data *r){(void)d;(void)c;(void)r;fallback++;}
'''
main='''int main(void){
 struct uvc_device dev={.xu_unit=4,.fov=75,.microphone=1};
 struct uvc_request_data out={.length=-1};
 uvc_events_process_control(&dev,UVC_GET_LEN,4,2,2,&out);
 if(out.length!=2||out.data[0]!=60||out.data[1]!=0){puts("FAIL: diagnostic selector must report 60-byte control");return 1;}
 out.length=-1;uvc_events_process_control(&dev,UVC_GET_CUR,4,1,8,&out);
 if(out.length!=8||out.data[0]!=1||out.data[1]!=75||out.data[5]!=1)return 2;
 out.length=-1;uvc_events_process_control(&dev,UVC_SET_CUR,4,2,61,&out);
 if(out.length!=-1)return 3;
 out.length=-1;uvc_events_process_control(&dev,UVC_GET_INFO,4,2,1,&out);
 if(out.length!=1||out.data[0]!=3)return 4;
 out.length=-1;uvc_events_process_control(&dev,UVC_SET_CUR,4,2,60,&out);
 if(out.length!=60||dev.control!=2||dev.control_entity!=4)return 5;
 struct usb_ctrlrequest request={.bRequestType=0xa1,.bRequest=UVC_GET_LEN,.wValue=0x0200,.wIndex=0x0400,.wLength=2};
 out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=2||fallback)return 6;
 request.bRequestType=0x21;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||fallback)return 7;
 request.bRequestType=0xa1;request.wValue=0x0201;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||fallback)return 8;
 request.wValue=0x0200;request.wIndex=0x0401;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||fallback)return 9;
 request.wIndex=0x0400;request.bRequest=UVC_GET_CUR;request.wLength=61;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||fallback)return 10;
 for(unsigned selector=3;selector<=4;selector++) {
  request=(struct usb_ctrlrequest){.bRequestType=0xa1,.bRequest=UVC_GET_LEN,.wValue=selector<<8,.wIndex=0x0400,.wLength=2};
  out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=2||out.data[0]!=32||fallback)return 11;
  request.bRequest=UVC_GET_INFO;request.wLength=1;
  out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=1||out.data[0]!=3||fallback)return 12;
  request.bRequest=UVC_SET_CUR;request.bRequestType=0x21;request.wLength=32;
  out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=32||dev.control!=(int)selector||dev.control_entity!=4)return 13;
  request.wLength=31;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||dev.control_entity)return 14;
  request.wLength=32;request.bRequestType=0xa1;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||dev.control_entity)return 15;
  request.bRequestType=0x21;request.wValue|=1;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||dev.control_entity)return 16;
  request.wValue=selector<<8;request.wIndex=0x0401;out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||dev.control_entity)return 17;
  request.wIndex=0x0400;request.bRequestType=0xa1;request.bRequest=UVC_GET_CUR;request.wLength=33;
  out.length=-1;uvc_events_process_setup(&dev,&request,&out);if(out.length!=-1||fallback)return 18;
 }
 puts("PASS: actual UVC diagnostic selector routing, malformed length and existing settings");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'control.c').write_text(prefix+src[start:end]+setup+main)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(root/'lib'),str(p/'control.c'),'-o',str(p/'test')],check=True)
 sys.exit(subprocess.run([str(p/'test')]).returncode)
