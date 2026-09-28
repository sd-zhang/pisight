#!/usr/bin/env python3
"""Run actual DWC2 preparation/timer functions with fake MMIO and time.

This checks software state and writes. It does not simulate bus tokens or
prove interrupt/timer latency on the Pi. An early EPENA write is the initial
regression: the unchanged start_req should fail the first behavioral case.
"""
from pathlib import Path
import re, subprocess, sys, tempfile
src=(Path(sys.argv[1])/'gadget.c').read_text()
def extract(name,optional=False):
 m=re.search(r'^(?:static )?(?:inline )?(?:enum \w+|\w+) '+name+r'\([^;]+?\)\n\{',src,re.M)
 if not m:
  if optional:return ''
  raise ValueError(name)
 pos=m.end(); depth=1
 while depth:
  depth+=(src[pos]=='{')-(src[pos]=='}');pos+=1
 return src[m.start():pos]
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32; typedef uint16_t u16; typedef uint64_t u64;
typedef u64 ktime_t;
#define BIT(n) (1u<<(n))
#define USB_SPEED_HIGH 3
#define DWC2_L0 0
#define TARGET_FRAME_INITIAL 0xffffffff
#define DSTS_SOFFN_LIMIT 0x3fff
#define DSTS_SOFFN_MASK (0x3fff<<8)
#define DSTS_SOFFN_SHIFT 8
#define DSTS_SUSPSTS 1
#define DSTS_ERRATICERR 8
#define DSTS 0
#define GINTSTS 1
#define DIEPCTL(i) (2+(i))
#define DOEPCTL(i) (6+(i))
#define DIEPTSIZ(i) (10+(i))
#define DOEPTSIZ(i) (14+(i))
#define DIEPDMA(i) (18+(i))
#define DOEPDMA(i) (22+(i))
#define DIEPINT(i) (26+(i))
#define DXEPINT_NAKINTRPT BIT(13)
#define DXEPINT_EPDISBLD BIT(1)
#define DXEPINT_XFERCOMPL BIT(0)
#define DXEPCTL_EPENA BIT(31)
#define DXEPCTL_EPDIS BIT(30)
#define DXEPCTL_SETODDFR BIT(29)
#define DXEPCTL_SETEVENFR BIT(28)
#define DXEPCTL_SNAK BIT(27)
#define DXEPCTL_CNAK BIT(26)
#define DXEPCTL_USBACTEP BIT(15)
#define DXEPCTL_STALL BIT(21)
#define DXEPTSIZ_MC(v) ((v)<<29)
#define DXEPTSIZ_PKTCNT(v) ((v)<<19)
#define DXEPTSIZ_XFERSIZE(v) (v)
#define GINTSTS_MODEMIS BIT(1)
#define GINTSTS_USBRST BIT(12)
#define GINTSTS_RESETDET BIT(23)
#define GINTSTS_ENUMDONE BIT(13)
#define GINTSTS_USBSUSP BIT(11)
#define GINTSTS_WKUPINT BIT(31)
#define GINTSTS_DISCONNINT BIT(29)
#define GINTSTS_CONIDSTSCHNG BIT(28)
#define GINTSTS_LPMTRANRCVD BIT(27)
#define GINTSTS_CURMODE_HOST BIT(0)
#define DWC2_EP0_SETUP 0
#define HRTIMER_MODE_ABS_PINNED 0
#define NSEC_PER_USEC 1000
#define IS_ENABLED(v) 1
#define CONFIG_HIGH_RES_TIMERS 1
#define dev_dbg(...) ((void)0)
#define dev_warn(...) ((void)0)
#define dev_err(...) ((void)0)
#define WARN_ON(v) ((void)(v))
#define DIV_ROUND_UP(n,d) (((n)+(d)-1)/(d))
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define spin_lock_irqsave(l,f) ((void)(l),(f)=0)
#define spin_unlock_irqrestore(l,f) ((void)(l),(void)(f))
#define max(a,b) ((a)>(b)?(a):(b))
enum hrtimer_restart {HRTIMER_NORESTART,HRTIMER_RESTART};
struct hrtimer {u64 expires;bool active;};
struct usb_request {u32 length,actual,dma,frame_number;bool zero;int status;};
struct dwc2_hsotg_req {struct usb_request req;void *saved_req_buf;};
struct dwc2_isoc_arm {
 struct hrtimer timer;
 struct dwc2_hsotg_req *request;
 bool initialized,prepared,pending;
 u32 target,session,epoch;
 u64 started_ns,deadline_ns;
 u64 scheduled,armed,late,early,cancelled,lateness_ns_max,resync,callbacks,callback_ns,callback_ns_max;
};
struct dwc2_hsotg_ep {
 struct dwc2_hsotg *parent;
 struct dwc2_hsotg_req *req;
 struct {u32 maxpacket;} ep;
 u32 index,dir_in,isochronous,interval,target_frame,diag_sessions;
 bool frame_overrun,send_zlp;
 u32 size_loaded,last_load,fifo_load,desc_list_dma;
 struct {bool valid;} deferred;
 struct {u32 serial,target,length,before_frame,after_frame;} diag_arm;
 struct dwc2_isoc_arm arm;
};
struct dwc2_hsotg {
 struct {int speed;} gadget;
 int lx_state,ep0_state,lock;
 bool bus_suspended,hibernated,in_ppd,ll_hw_enabled,dma,ddma;
 u32 frame_number,num_of_eps,arm_epoch;
 struct dwc2_hsotg_ep *eps_in[4];
};
static u32 regs[32],live;
static u64 now;
static unsigned failures,cases,epena_writes,completions,enabled_interrupts,reads;
static bool highres=true; static bool forbidden_mmio; static int advance_at_epint;
static u64 ktime_get_ns(void){return now;}
static bool hrtimer_is_hres_active(struct hrtimer *t){return highres;}
static ktime_t ns_to_ktime(u64 v){return v;}
static void hrtimer_start(struct hrtimer *t,ktime_t v,int mode){t->expires=v;t->active=true;}
static int hrtimer_try_to_cancel(struct hrtimer *t){t->active=false;return 1;}
static u32 dwc2_readl(struct dwc2_hsotg *h,u32 r){reads++;if(r==DIEPINT(3) && advance_at_epint){if(advance_at_epint==1){live=108;regs[DSTS]=live<<8;}else{regs[GINTSTS]|=GINTSTS_USBRST;}advance_at_epint=0;}if(forbidden_mmio){fprintf(stderr,"forbidden MMIO\n");failures++;}return regs[r];}
static void dwc2_writel(struct dwc2_hsotg *h,u32 v,u32 r){if(forbidden_mmio)failures++;regs[r]=v;if(r==DIEPCTL(3)&&(v&DXEPCTL_EPENA))epena_writes++;}
static u32 dwc2_hsotg_read_frameno(struct dwc2_hsotg *h){return live;}
static bool using_dma(struct dwc2_hsotg *h){return h->dma;}
static bool using_desc_dma(struct dwc2_hsotg *h){return h->ddma;}
static u32 get_ep_limit(struct dwc2_hsotg_ep *e){return 1024;}
static u32 dwc2_gadget_get_chain_limit(struct dwc2_hsotg_ep *e){return 1024;}
static void dwc2_gadget_config_nonisoc_xfer_ddma(struct dwc2_hsotg_ep *e,u32 d,u32 l){}
static void dwc2_hsotg_write_fifo(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e,struct dwc2_hsotg_req *r){}
static void dwc2_hsotg_ctrl_epint(struct dwc2_hsotg *h,int idx,int dir,int en){enabled_interrupts+=en;}
static void dwc2_isoc_diag_miss(struct dwc2_hsotg_ep *e,int reason,int burst,struct dwc2_hsotg_req *r){}
static void dwc2_hsotg_complete_request(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e,struct dwc2_hsotg_req *r,int result){e->req=NULL;completions++;}
'''
names=['dwc2_isoc_epoch_valid','dwc2_isoc_arm_cancel','dwc2_gadget_cancel_isoc_arming',
'dwc2_isoc_arm_expired','dwc2_isoc_write_epena','dwc2_isoc_arm_timer','dwc2_isoc_prepare_arm']
functions=extract('dwc2_gadget_target_frame_elapsed')+'\n'+'\n'.join(extract(n,True) for n in names)+'\n'+extract('dwc2_hsotg_start_req')
has_timer='dwc2_isoc_arm_timer' in src
suffix=r'''
static void check(bool v,const char *s){cases++;if(!v){failures++;printf("FAIL %s\n",s);}}
static void setup(struct dwc2_hsotg *h,struct dwc2_hsotg_ep *e,struct dwc2_hsotg_req *r){
 memset(h,0,sizeof(*h));memset(e,0,sizeof(*e));memset(r,0,sizeof(*r));memset(regs,0,sizeof(regs));
 live=100;now=1000000000;epena_writes=completions=enabled_interrupts=reads=0;forbidden_mmio=false;advance_at_epint=0;highres=true;
 h->gadget.speed=USB_SPEED_HIGH;h->dma=true;h->ll_hw_enabled=true;h->frame_number=live;h->eps_in[3]=e;h->num_of_eps=4;
 e->parent=h;e->index=3;e->dir_in=1;e->isochronous=1;e->interval=8;e->target_frame=108;e->ep.maxpacket=196;e->diag_sessions=1;e->arm.initialized=true;
 r->req.length=192;r->req.dma=0x1000;r->req.status=-EINPROGRESS;
 regs[DIEPCTL(3)]=DXEPCTL_USBACTEP;regs[DSTS]=live<<8;
}
static void tick(struct dwc2_hsotg *h,u32 frame,u64 ns){live=frame;h->frame_number=frame;regs[DSTS]=frame<<8;now=ns;}
int main(void){struct dwc2_hsotg h;struct dwc2_hsotg_ep e;struct dwc2_hsotg_req r;
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);
 check(epena_writes==0,"future audio does not enable hardware at previous completion");
 check(e.req==&r && e.size_loaded==192 && e.last_load==0 && enabled_interrupts==1,"prepared request owns DMA and completion accounting");
 check(e.arm.pending && e.arm.prepared && e.arm.timer.expires==1000625000,"one timer targets three microframes before audio poll");
 check(e.diag_arm.serial==0,"preparation is not reported as actual arm");
'''
if has_timer:
 suffix+=r'''
 tick(&h,105,1000625000);dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==1 && !e.arm.pending && !e.arm.prepared && e.req==&r,"on-time callback enables same prepared request");
 check(e.diag_arm.serial==1 && e.diag_arm.before_frame==105 && e.diag_arm.after_frame==105 && e.diag_arm.target==108,"diagnostics describe actual enable");
 setup(&h,&e,&r);e.target_frame=103;dwc2_hsotg_start_req(&h,&e,&r,false);
 check(epena_writes==1&&!e.arm.pending,"near-target audio uses immediate enable");
 setup(&h,&e,&r);e.interval=1;e.target_frame=101;dwc2_hsotg_start_req(&h,&e,&r,false);
 check(epena_writes==1&&!e.arm.pending,"video interval one remains immediate");
 setup(&h,&e,&r);h.ddma=true;dwc2_hsotg_start_req(&h,&e,&r,false);
 check(epena_writes==1&&!e.arm.pending,"descriptor DMA remains immediate");
 setup(&h,&e,&r);h.gadget.speed=2;dwc2_hsotg_start_req(&h,&e,&r,false);
 check(epena_writes==1&&!e.arm.pending,"full-speed remains immediate");
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,108,1001000000);dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==0&&!e.arm.pending&&e.arm.prepared&&e.arm.late==1,"late callback leaves ownership for NAK recovery without stale arm");
 check(dwc2_isoc_arm_expired(&e),"late prepared request is expired");
 setup(&h,&e,&r);h.frame_number=live=16375;regs[DSTS]=live<<8;e.target_frame=16383;dwc2_hsotg_start_req(&h,&e,&r,false);
 tick(&h,0,1001125000);dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==0 && dwc2_isoc_arm_expired(&e),"late preparation recovers across frame wrap");
 setup(&h,&e,&r);h.frame_number=live=16380;regs[DSTS]=live<<8;e.target_frame=4;e.frame_overrun=true;dwc2_hsotg_start_req(&h,&e,&r,false);
 tick(&h,1,1000625000);dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==1,"future target across wrap arms normally");
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,100,1000625000);dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==1&&!e.arm.pending&&e.arm.early==1,"missing SOF uses single early fallback not timer loop");
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);dwc2_isoc_arm_cancel(&e);forbidden_mmio=true;dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==0&&!e.arm.pending,"cancelled callback performs no register access");
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);dwc2_gadget_cancel_isoc_arming(&h);forbidden_mmio=true;dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==0&&!e.arm.pending&&e.arm.prepared,"power cancellation preserves unarmed ownership without MMIO");
 for(int mode=0;mode<4;mode++){
  setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,105,1000625000);
  if(mode==0)h.ll_hw_enabled=false;if(mode==1)h.hibernated=true;if(mode==2)h.in_ppd=true;if(mode==3)h.bus_suspended=true;
  forbidden_mmio=true;dwc2_isoc_arm_timer(&e.arm.timer);check(epena_writes==0,"inactive controller rejects callback before MMIO");
 }
 for(int mode=0;mode<5;mode++){
  setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,105,1000625000);
  if(mode==0)e.diag_sessions++;if(mode==1)e.target_frame++;if(mode==2)e.req=NULL;if(mode==3)h.arm_epoch++;if(mode==4)regs[GINTSTS]=GINTSTS_USBRST;
  dwc2_isoc_arm_timer(&e.arm.timer);check(epena_writes==0,"stale request or bus epoch cannot enable endpoint");
 }
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,105,1000624999);dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==0 && e.arm.pending,"old callback cannot run newer preparation before its deadline");
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,105,1000625000);regs[DIEPCTL(3)]=0;dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==0,"disabled endpoint cannot be resurrected");
 setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,105,1000625000);regs[DIEPINT(3)]=DXEPINT_NAKINTRPT;dwc2_isoc_arm_timer(&e.arm.timer);
 check(epena_writes==0,"pending NAK must be reconciled before enabling");
'''
if has_timer:
 suffix+=r'''
 setup(&h,&e,&r);highres=false;dwc2_hsotg_start_req(&h,&e,&r,false);
 check(epena_writes==1&&!e.arm.pending,"runtime low-resolution timers keep immediate audio path");
 for(int event=1;event<=2;event++){
  setup(&h,&e,&r);dwc2_hsotg_start_req(&h,&e,&r,false);tick(&h,107,1000900000);advance_at_epint=event;
  dwc2_isoc_arm_timer(&e.arm.timer);check(epena_writes==0,"frame or reset crossing during final arm checks prevents stale enable");
 }
'''
suffix+='printf("%u checks, %u failures\\n",cases,failures);return failures?1:0;}'
with tempfile.TemporaryDirectory(prefix='pisight-arm-test-') as d:
 p=Path(d)/'test.c';p.write_text(prefix+functions+suffix)
 c=subprocess.run(['cc','-std=c11','-Wall','-Wno-unused-function','-Wno-unused-parameter',str(p),'-o',str(Path(d)/'test')],capture_output=True,text=True)
 if c.returncode: print(c.stderr);sys.exit(c.returncode)
 if c.stderr:print(c.stderr)
 sys.exit(subprocess.run([str(Path(d)/'test')]).returncode)
