#!/usr/bin/env python3
"""Replay actual DWC2 IRQ/queue functions with fake MMIO (not a USB emulator).

Extracts complete functions except epint's unrelated tail after NAK handling.
DMA programming, locks and gadget callbacks are modeled; queue retirement,
completion/start ordering and frame arithmetic are production code.
"""
from pathlib import Path
import subprocess, sys, tempfile
source = Path(sys.argv[1]).read_text()
def extract(name):
    import re
    m = re.search(r'^static (?:inline )?\w+ '+name+r'\([^;]+?\)\n\{', source, re.M)
    assert m, name
    start=m.start(); pos=m.end(); depth=1
    while depth:
        depth += (source[pos]=='{')-(source[pos]=='}'); pos+=1
    body=source[start:pos]
    if name=='dwc2_hsotg_epint':
        body=body.split('\n\tif (ints & DXEPINT_AHBERR)')[0]+'\n}'
    return body
prefix=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <errno.h>
#include <string.h>
typedef uint32_t u32; typedef uint16_t u16; typedef uint64_t u64;
#define DSTS_SOFFN_LIMIT 0x3fff
#define TARGET_FRAME_INITIAL 0xffffffff
#define USB_SPEED_HIGH 3
#define DWC2_EP0_SETUP 0
#define DWC2_EP0_DATA_IN 1
#define DWC2_EP0_STATUS_IN 2
#define DXEPINT_XFERCOMPL 1
#define DXEPINT_EPDISBLD 2
#define DXEPINT_SETUP 8
#define DXEPINT_OUTTKNEPDIS 16
#define DXEPINT_SETUP_RCVD 32768
#define DXEPINT_NAKINTRPT 8192
#define DXEPCTL_STALL (1u<<21)
#define DXEPCTL_EPTYPE_BULK (2u<<18)
#define DXEPCTL_EPENA (1u<<31)
#define DXEPCTL_SETODDFR (1u<<29)
#define DXEPCTL_SETEVENFR (1u<<28)
#define DCTL_CGNPINNAK (1u<<8)
#define DCTL_GOUTNAKSTS (1u<<3)
#define DCTL_CGOUTNAK (1u<<10)
#define DIEPINT(i) 0
#define DOEPINT(i) 1
#define DIEPCTL(i) 2
#define DOEPCTL(i) 3
#define DIEPTSIZ(i) 4
#define DOEPTSIZ(i) 5
#define DCTL 6
#define GINTSTS 7
#define GINTMSK 8
#define GINTSTS_SOF (1u<<3)
#define GINTSTS_CURMODE_HOST 1
#define DXEPTSIZ_XFERSIZE_GET(v) ((v)&0x7ffff)
#define dev_dbg(...) ((void)0)
#define dev_err(...) ((void)0)
#define spin_unlock(...) ((void)0)
#define spin_lock(...) ((void)0)
struct list_head { struct list_head *next,*prev; };
static void init(struct list_head *h){h->next=h->prev=h;}
static bool list_empty(struct list_head *h){return h->next==h;}
static void append(struct list_head *q,struct list_head *h){q->next=h;q->prev=h->prev;h->prev->next=q;h->prev=q;}
static void list_del_init(struct list_head *q){q->prev->next=q->next;q->next->prev=q->prev;init(q);}
#define container(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
struct usb_request { int status,actual,length,zero,frame_number; void *complete; };
struct dwc2_hsotg_req { struct usb_request req; struct list_head queue; int id; };
struct usb_ep { const char *name; };
struct dwc2_hsotg_ep {
 struct dwc2_hsotg *parent; struct dwc2_hsotg_req *req; struct list_head queue; struct usb_ep ep;
 unsigned target_frame,interval,index,dir_in,isochronous,frame_overrun,fifo_index,diag_irq;
 int size_loaded,last_load,send_zlp;
 unsigned diag_sessions;
 struct {u32 serial,target,before_frame,after_frame,length;} diag_arm;
 struct {u64 ns;u32 serial,session,target,epoch;bool valid;} deferred;
};
struct dwc2_hsotg { struct {unsigned nak[16],complete[16],recovery_epoch,deferred_completed;} irq_diag; struct {int speed;} gadget; struct {int g_dma,g_dma_desc,service_interval;} params;
 unsigned frame_number; int ep0_state,test_mode,lock; void *dev; struct dwc2_hsotg_ep *ep; };
static u32 regs[9],irq,live;
static int starts,flushes,flush_after_start,givebacks,ids[40000],statuses[40000],frames[40000],requeue,ddma,outdone,setups;
static struct dwc2_hsotg_req *get_ep_head(struct dwc2_hsotg_ep *e){return list_empty(&e->queue)?NULL:container(e->queue.next,struct dwc2_hsotg_req,queue);}
static u32 dwc2_readl(struct dwc2_hsotg *h,int reg){return regs[reg];}
static void dwc2_writel(struct dwc2_hsotg *h,u32 val,int reg){regs[reg]=val;}
static u32 dwc2_hsotg_read_frameno(struct dwc2_hsotg *h){return live;}
static u32 dwc2_gadget_read_ep_interrupts(struct dwc2_hsotg *h,unsigned idx,int dir){return irq;}
static struct dwc2_hsotg_ep *index_to_ep(struct dwc2_hsotg *h,unsigned idx,int dir){return h->ep;}
static void dwc2_hsotg_start_req(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e,struct dwc2_hsotg_req *r,bool continuing){e->req=r;starts++;regs[2]|=DXEPCTL_EPENA;}
static void dwc2_hsotg_txfifo_flush(struct dwc2_hsotg *h,int idx){flushes++;if(starts)flush_after_start++;}
static void dwc2_hsotg_ep_stop_xfr(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e){regs[2]&=~DXEPCTL_EPENA;dwc2_hsotg_txfifo_flush(h,e->index);}
static void dwc2_isoc_diag_miss(struct dwc2_hsotg_ep *e,int reason,unsigned burst,struct dwc2_hsotg_req *r){}
static void dwc2_hsotg_unmap_dma(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e,struct dwc2_hsotg_req *r){}
static void dwc2_hsotg_handle_unaligned_buf_complete(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e,struct dwc2_hsotg_req *r){}
static void usb_gadget_giveback_request(struct usb_ep *ep,struct usb_request *r){
 struct dwc2_hsotg_ep *e=container(ep,struct dwc2_hsotg_ep,ep);
 struct dwc2_hsotg_req *hr=container(r,struct dwc2_hsotg_req,req);
 if(givebacks>=40000)abort();
 ids[givebacks]=hr->id;statuses[givebacks]=r->status;frames[givebacks++]=r->frame_number;
 // Model callback queue refill, not MMIO or immediate start. A next request
 // remains queued during recovery, as with the UVC prequeued request pool.
 if(requeue){r->status=-EINPROGRESS;append(&hr->queue,&e->queue);}
}
static int dwc2_hsotg_set_test_mode(struct dwc2_hsotg *h,int mode){return 0;}
static void dwc2_hsotg_stall_ep0(struct dwc2_hsotg *h){}
static void dwc2_hsotg_enqueue_setup(struct dwc2_hsotg *h){setups++;}
static int dwc2_gadget_get_xfersize_ddma(struct dwc2_hsotg_ep *e){return regs[4];}
static void dwc2_hsotg_program_zlp(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e){}
static void dwc2_hsotg_ep0_zlp(struct dwc2_hsotg *h,bool in){}
static void dwc2_gadget_start_isoc_ddma(struct dwc2_hsotg_ep *e){ddma++;}
static void dwc2_gadget_complete_isoc_request_ddma(struct dwc2_hsotg_ep *e){ddma++;}
static void dwc2_hsotg_handle_outdone(struct dwc2_hsotg *h,unsigned idx){outdone++;}
'''
if 'dwc2_isoc_prepare_arm(' in source:
    prefix=prefix.replace('struct dwc2_hsotg_ep {', '''
struct hrtimer {bool active;};
#define HRTIMER_MODE_ABS_PINNED 0
static u64 ns_to_ktime(u64 v){return v;}
static void hrtimer_start(struct hrtimer *t,u64 v,int mode){t->active=true;}
struct dwc2_isoc_arm {struct hrtimer timer;struct dwc2_hsotg_req *request;bool initialized,prepared,pending,waiting_sof;u32 target,session,epoch;u64 started_ns,deadline_ns,scheduled,armed,late,early,cancelled,lateness_ns_max,resync,callbacks,callback_ns,callback_ns_max;};
static u64 ktime_get_ns(void){return 1001125000;}
static int hrtimer_try_to_cancel(struct hrtimer *t){t->active=false;return 1;}
#define spin_lock_irqsave(l,f) ((void)(l),(f)=0)
#define spin_unlock_irqrestore(l,f) ((void)(l),(void)(f))
struct dwc2_hsotg_ep {struct dwc2_isoc_arm arm;''')
    prefix=prefix.replace('struct dwc2_hsotg {', 'struct dwc2_hsotg {u32 arm_epoch,num_of_eps;struct dwc2_hsotg_ep *eps_in[4];bool arm_sof_enabled;int lx_state;bool ll_hw_enabled,bus_suspended,hibernated,in_ppd;')
    prefix=prefix.replace('starts,flushes,', 'forbidden_reads,stops,timer_at_giveback,starts,flushes,')
    prefix=prefix.replace('{regs[2]&=~DXEPCTL_EPENA;', '{stops++;regs[2]&=~DXEPCTL_EPENA;')
    prefix=prefix.replace('if(givebacks>=40000)abort();','''if(e->arm.pending)timer_at_giveback++;if(givebacks>=40000)abort();
 if(requeue==3)e->parent->arm_epoch++;
 if(requeue==4)e->parent->ll_hw_enabled=false;
 if(requeue==5)e->parent->lx_state=2;
 if(requeue==2){e->req=hr;e->arm.pending=true;e->arm.prepared=true;e->arm.target=e->target_frame;e->arm.request=hr;}
''')
    prefix=prefix.replace('{return live;}', '{if(!h->ll_hw_enabled)forbidden_reads++;return live;}')
    prefix += '''
#define DWC2_L0 0
static struct dwc2_hsotg_req *our_req(struct usb_request *r){return container(r,struct dwc2_hsotg_req,req);}
static struct dwc2_hsotg_ep *our_ep(struct usb_ep *e){return container(e,struct dwc2_hsotg_ep,ep);}
static bool on_list(struct dwc2_hsotg_ep *e,struct dwc2_hsotg_req *r){struct list_head *p=e->queue.next;while(p!=&e->queue){if(p==&r->queue)return true;p=p->next;}return false;}
'''
names=['using_dma','using_desc_dma','dwc2_gadget_incr_frame_num','dwc2_gadget_dec_frame_num_by_one','dwc2_gadget_target_frame_elapsed','dwc2_gadget_start_next_request','dwc2_hsotg_complete_request','dwc2_hsotg_complete_in','dwc2_gadget_handle_ep_disabled','dwc2_gadget_handle_out_token_ep_disabled','dwc2_gadget_handle_nak','dwc2_hsotg_epint']
tests=r'''
static int failures,cases;
static void run(const char *name,unsigned flags,unsigned frame,unsigned interval,int refill,int count,int payload,int iso,int desc,int index,int dir){
 struct dwc2_hsotg h={.gadget.speed=USB_SPEED_HIGH,.params={.g_dma=1,.g_dma_desc=desc},.frame_number=frame};
 struct dwc2_hsotg_ep e={.parent=&h,.target_frame=frame,.interval=interval,.index=index,.dir_in=dir,.isochronous=iso,.size_loaded=payload};
 struct dwc2_hsotg_req reqs[2]={0};
 if(strcmp(name,"slave_combined")==0)h.params.g_dma=0;
 h.ep=&e;init(&e.queue); memset(regs,0,sizeof(regs)); live=frame;irq=flags;requeue=refill;
 starts=flushes=flush_after_start=givebacks=ddma=outdone=setups=0;
 for(int i=0;i<count;i++){reqs[i].id=i+1;reqs[i].req.length=payload;reqs[i].req.status=-EINPROGRESS;reqs[i].req.complete=(void*)1;append(&reqs[i].queue,&e.queue);}
 e.req=&reqs[0];
 if(strncmp(name,"deferred_",9)==0) {
  e.deferred.valid=true;e.deferred.serial=e.diag_arm.serial=42;
  e.deferred.target=e.diag_arm.target=frame;
  e.deferred.session=e.diag_sessions=1;
  if(strcmp(name,"deferred_old_session")==0)e.diag_sessions++;
 }
 dwc2_hsotg_epint(&h,index,dir);
 bool ok;
 if(desc) ok=ddma==1; // DDMA completion branch dispatch is unchanged.
 else if(!dir) ok=outdone==1&&givebacks==0;
 else if(!iso) ok=givebacks==1&&ids[0]==1&&statuses[0]==0;
 else {
  bool recovery=flags&(DXEPINT_EPDISBLD|DXEPINT_NAKINTRPT);
  bool nak=flags&DXEPINT_NAKINTRPT;
  ok=givebacks==1&&ids[0]==1&&statuses[0]==(recovery?-ENODATA:0)&&frames[0]==(int)frame&&e.target_frame==((frame+interval)&DSTS_SOFFN_LIMIT)&&flush_after_start==0;
  ok &= starts==((!recovery||nak)&&(count>1||refill)?1:0);
 }
 if(strncmp(name,"deferred_",9)==0)
  ok &= !e.deferred.valid && h.irq_diag.deferred_completed==
        (unsigned)(strcmp(name,"deferred_success")==0);
 printf("%s %s: callbacks=%d first=%d/status=%d starts=%d flush_after_start=%d target=%u\n",ok?"PASS":"FAIL",name,givebacks,givebacks?ids[0]:0,givebacks?statuses[0]:0,starts,flush_after_start,e.target_frame);
 if(strcmp(name,"resync_after_combined")==0 && ok){
  live=frame+interval;h.frame_number=live;irq=DXEPINT_NAKINTRPT;regs[2]=0;
  dwc2_hsotg_epint(&h,index,dir);
  bool resumed=givebacks==2&&ids[1]==2&&statuses[1]==-ENODATA&&frames[1]==(int)live&&starts==1&&e.req==&reqs[0]&&e.target_frame==live+interval&&flush_after_start==0;
  live+=interval;h.frame_number=live;irq=DXEPINT_XFERCOMPL;regs[2]=0;
  dwc2_hsotg_epint(&h,index,dir);
  resumed &= givebacks==3&&ids[2]==1&&statuses[2]==0&&frames[2]==(int)live&&starts==2&&e.req==&reqs[1];
  printf("%s subsequent NAK resumes queue and next completion succeeds\n",resumed?"PASS":"FAIL");
  ok &= resumed;
 }
 cases++;failures+=!ok;
}
int main(void){
 setbuf(stdout,NULL);
 run("recorded_irq_0x3",3,2361,1,0,2,1024,1,0,1,1);
 run("resync_after_combined",3,2361,1,1,2,1024,1,0,1,1);
 run("recorded_irq_refill",3,2361,1,1,2,1024,1,0,1,1);
 run("single_request_no_refill",3,2361,1,0,1,1024,1,0,1,1);
 run("empty_packet",3,2361,1,0,2,0,1,0,1,1);
 run("slave_combined",3,2361,1,0,2,1024,1,0,1,1);
 run("audio_interval",3,2360,8,0,2,96,1,0,3,1);
 run("wrap_refill",3,16383,1,1,2,1024,1,0,1,1);
 run("wrap_interval8",3,16376,8,1,2,96,1,0,3,1);
 run("completion_only",1,2361,1,0,2,1024,1,0,1,1);
 run("disabled_only",2,2361,1,0,2,1024,1,0,1,1);
 run("nak_only",8192,2361,1,0,2,1024,1,0,1,1);
 run("completion_nak",8193,2361,1,0,2,1024,1,0,1,1);
 run("completion_disabled_nak",8195,2361,1,0,2,1024,1,0,1,1);
 run("bulk_completion",1,2361,1,0,2,1024,0,0,1,1);
 run("bulk_combined",3,2361,1,0,2,1024,0,0,1,1);
 run("ep0_completion",1,2361,1,0,1,64,0,0,0,1);
 run("ddma_completion",1,2361,1,0,2,1024,1,1,1,1);
 run("out_completion",1,2361,1,0,2,1024,1,0,1,0);
#ifdef HAS_DEFERRED_RECOVERY
 run("deferred_success",1,2361,1,0,2,1024,1,0,1,1);
 run("deferred_failure",2,2361,1,0,2,1024,1,0,1,1);
 run("deferred_old_session",1,2361,1,0,2,1024,1,0,1,1);
#endif
 printf("%d cases, %d failures\n",cases,failures);return failures?1:0;
}
'''
with tempfile.TemporaryDirectory(prefix='dwc2-coalesced-') as tmp:
    src=Path(tmp)/'replay.c'; exe=Path(tmp)/'replay'
    if 'static bool dwc2_isoc_deferred_matches(' in source:
        prefix += '\n#define HAS_DEFERRED_RECOVERY 1\n'
        names.insert(0, 'dwc2_isoc_deferred_matches')
    if 'dwc2_isoc_prepare_arm(' in source:
        names[0:0]=['dwc2_isoc_arm_cancel','dwc2_isoc_arm_expired']
        names.append('dwc2_hsotg_ep_dequeue')
        tests=tests.replace('int main(void){',r'''
static void prepared_cases(void){
 for(int mode=0;mode<79;mode++){
  struct dwc2_hsotg h={.gadget.speed=USB_SPEED_HIGH,.params.g_dma=1,.frame_number=100};
  struct dwc2_hsotg_ep e={.parent=&h,.target_frame=108,.interval=8,.index=3,.dir_in=1,.isochronous=1,.diag_sessions=1};
  struct dwc2_hsotg_req rs[2]={0};
  h.ll_hw_enabled=true;h.num_of_eps=4;h.eps_in[3]=&e;h.ep=&e;init(&e.queue);memset(regs,0,sizeof(regs));live=100;requeue=0;
  starts=flushes=flush_after_start=givebacks=stops=timer_at_giveback=forbidden_reads=0;
  for(int i=0;i<2;i++){rs[i].id=i+1;rs[i].req.status=-EINPROGRESS;rs[i].req.complete=(void*)1;append(&rs[i].queue,&e.queue);}
  e.req=&rs[0];e.arm=(struct dwc2_isoc_arm){.initialized=true,.prepared=true,.pending=true,.target=108,.session=1,.request=&rs[0],.started_ns=1000000000};
  bool ok=false;
  if(mode==0){
   dwc2_hsotg_ep_dequeue(&e.ep,&rs[0].req);
   ok=stops==0&&givebacks==1&&timer_at_giveback==0&&!e.arm.pending;
  }
  if(mode==1){
   dwc2_hsotg_ep_dequeue(&e.ep,&rs[1].req);
   ok=stops==0&&givebacks==1&&e.req==&rs[0]&&e.arm.pending;
  }
  if(mode==2){
   e.target_frame=e.arm.target=16383;live=h.frame_number=0;
   dwc2_gadget_handle_nak(&e);
   ok=givebacks==1&&frames[0]==16383&&statuses[0]==-ENODATA&&e.target_frame==7&&starts==1&&!e.arm.pending&&e.req==&rs[1];
  }
  if(mode==3){
   dwc2_gadget_handle_nak(&e);
   ok=givebacks==0&&e.req==&rs[0]&&e.arm.pending;
  }
  if(mode==4){
   dwc2_hsotg_complete_request(&h,&e,&rs[0],-ESHUTDOWN);
   ok=givebacks==1&&timer_at_giveback==0&&!e.arm.pending;
  }
  if(mode==5 || mode==6){
   e.arm.started_ns=998000000;
   if(mode==5){e.target_frame=e.arm.target=108;live=h.frame_number=101;}
   else {e.target_frame=e.arm.target=110;live=h.frame_number=100;}
   dwc2_gadget_handle_nak(&e);
   ok=givebacks==1&&statuses[0]==-ENODATA&&e.target_frame==(unsigned)(mode==5?108:102)&&e.req==&rs[1];
  }
  if(mode==7){
   e.target_frame=e.arm.target=16383;live=h.frame_number=0;requeue=2;list_del_init(&rs[1].queue);
   dwc2_gadget_handle_nak(&e);
   ok=givebacks==1&&timer_at_giveback==0&&e.target_frame==7&&e.arm.target==7&&e.arm.pending&&e.req==&rs[0];
  }
  if(mode>=8 && mode<72){
   unsigned cur=(mode-8)/8,phase=(mode-8)%8;
   e.target_frame=e.arm.target=96+phase;live=h.frame_number=cur;e.arm.started_ns=998000000;
   dwc2_gadget_handle_nak(&e);
   unsigned want=phase>cur?phase:phase+8;
   ok=givebacks==1&&e.target_frame==want&&e.req==&rs[1];
  }
  if(mode>=72 && mode<75){
   e.target_frame=e.arm.target=16383;live=h.frame_number=0;requeue=mode-69;
   dwc2_gadget_handle_nak(&e);
   ok=givebacks==1&&starts==0&&forbidden_reads==0;
  }
  if(mode>=75){
   e.arm.pending=false;e.arm.waiting_sof=true;h.arm_sof_enabled=true;regs[GINTMSK]=GINTSTS_SOF;
   if(mode==75){dwc2_gadget_handle_nak(&e);ok=!e.arm.pending&&e.arm.waiting_sof&&givebacks==0;}
   if(mode==76){dwc2_hsotg_ep_dequeue(&e.ep,&rs[0].req);ok=!e.arm.pending&&!e.arm.waiting_sof&&givebacks==1&&!(regs[GINTMSK]&GINTSTS_SOF);}
   if(mode==77){dwc2_hsotg_complete_request(&h,&e,&rs[0],-ESHUTDOWN);ok=!e.arm.waiting_sof&&givebacks==1&&!(regs[GINTMSK]&GINTSTS_SOF);}
   if(mode==78){e.target_frame=e.arm.target=16383;live=h.frame_number=0;dwc2_gadget_handle_nak(&e);ok=givebacks==1&&frames[0]==16383&&!e.arm.waiting_sof&&!(regs[GINTMSK]&GINTSTS_SOF);}
  }
  printf("%s prepared lifecycle %d\n",ok?"PASS":"FAIL",mode);cases++;failures+=!ok;
 }
}
int main(void){prepared_cases();''')
    if 'dwc2_isoc_sof_sync(' in source:
        names.insert(0,'dwc2_isoc_sof_sync')
    else:
        tests=tests.replace('mode<79','mode<75')
    src.write_text(prefix+'\n'.join(extract(n) for n in names)+tests)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable','-fsanitize=undefined','-o',str(exe),str(src)],check=True)
    sys.exit(subprocess.run([str(exe)],timeout=10).returncode)
