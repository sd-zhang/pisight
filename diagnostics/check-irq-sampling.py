#!/usr/bin/env python3
"""Run actual diagnostic sampling functions against explicit clock/MMIO inputs."""
from pathlib import Path
import re, subprocess, sys, tempfile
root=Path(sys.argv[1]); source=(root/'gadget.c').read_text()
def extract(name):
    m=re.search(r'^static (?:void|bool) '+name+r'\([^;]+?\)\n\{',source,re.M)
    assert m,name
    pos=m.end();depth=1
    while depth:
        depth+=(source[pos]=='{')-(source[pos]=='}');pos+=1
    return source[m.start():pos]
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
typedef uint32_t u32; typedef uint64_t u64;
#include "isoc-diag.h"
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define USB_SPEED_HIGH 3
#define DWC2_L0 0
#define DSTS 0
#define DCFG 1
#define GINTSTS 33
#define DIEPINT(n) (2+(n))
#define DIEPTSIZ(n) (18+(n))
#define DSTS_SOFFN_MASK (0x3fff<<8)
#define DSTS_SOFFN_SHIFT 8
#define DSTS_SUSPSTS 1
#define DSTS_ERRATICERR 8
#define GINTSTS_USBRST (1<<12)
#define GINTSTS_RESETDET (1<<23)
#define GINTSTS_ENUMDONE (1<<13)
#define GINTSTS_USBSUSP (1<<11)
#define GINTSTS_WKUPINT (1u<<31)
#define GINTSTS_DISCONNINT (1u<<29)
#define GINTSTS_IEPINT (1<<18)
#define GINTSTS_OEPINT (1<<19)
#define GINTSTS_INCOMPL_SOIN (1<<20)
#define GINTSTS_MODEMIS (1<<1)
#define GINTSTS_CONIDSTSCHNG (1<<28)
struct dwc2_hsotg {struct dwc2_irq_diag irq_diag;struct {int speed;} gadget;int lx_state;bool bus_suspended;u32 frame_number;};
struct dwc2_hsotg_ep {u32 index,target_frame,diag_sessions;struct dwc2_diag_arm diag_arm;};
static u32 regs[34];static u64 now;
static u64 ktime_get_ns(void){u64 t=now;now+=1000;return t;}
static u32 dwc2_readl(struct dwc2_hsotg *h,u32 reg){(void)h;return regs[reg];}
static bool using_dma(struct dwc2_hsotg *h){(void)h;return true;}
static bool using_desc_dma(struct dwc2_hsotg *h){(void)h;return false;}
'''
tests=r'''
static void snapshot(struct dwc2_hsotg *h,u32 frame,u64 ns,u32 status){regs[DSTS]=frame<<8;h->frame_number=frame;now=ns;dwc2_diag_irq_snapshot(h,status,~0u);}
static void prepare(struct dwc2_hsotg *h){memset(h,0,sizeof(*h));memset(regs,0,sizeof(regs));h->gadget.speed=USB_SPEED_HIGH;snapshot(h,100,99000,0);snapshot(h,101,126000,GINTSTS_INCOMPL_SOIN);}
int main(void){
 struct dwc2_hsotg h;
 struct dwc2_hsotg_ep e={.index=1,.target_frame=101,.diag_sessions=2,.diag_arm={.serial=3,.target=101,.before_frame=100,.after_frame=100,.length=2048}};
 prepare(&h);assert(h.irq_diag.before_eopf==1);
 dwc2_diag_disable_decision(&h,&e,0x80000000);
 assert(h.irq_diag.selected_early==1&&h.irq_diag.early_count==1);
 assert(h.irq_diag.early_samples[0].arm.serial==3&&h.irq_diag.early_samples[0].arm.length==2048);
 prepare(&h);regs[DSTS]|=DSTS_ERRATICERR;dwc2_diag_disable_decision(&h,&e,0x80000000);assert(h.irq_diag.selected_early==0);
 prepare(&h);regs[GINTSTS]=GINTSTS_USBRST;dwc2_diag_disable_decision(&h,&e,0x80000000);assert(h.irq_diag.selected_early==0);
 prepare(&h);now=225000;dwc2_diag_disable_decision(&h,&e,0x80000000);assert(h.irq_diag.selected_early==0);
 prepare(&h);regs[DSTS]=102<<8;dwc2_diag_disable_decision(&h,&e,0x80000000);assert(h.irq_diag.selected_early==0);
 prepare(&h);e.target_frame=100;dwc2_diag_disable_decision(&h,&e,0x80000000);assert(h.irq_diag.selected_early==0);e.target_frame=101;
 prepare(&h);snapshot(&h,102,127000,GINTSTS_USBRST|GINTSTS_INCOMPL_SOIN);assert(!h.irq_diag.current_valid);snapshot(&h,103,128000,GINTSTS_INCOMPL_SOIN);assert(!h.irq_diag.current_valid);
 prepare(&h);h.bus_suspended=true;snapshot(&h,102,127000,GINTSTS_INCOMPL_SOIN);assert(!h.irq_diag.current_valid);
 prepare(&h);h.gadget.speed=1;snapshot(&h,102,127000,GINTSTS_INCOMPL_SOIN);assert(!h.irq_diag.current_valid);
 prepare(&h);for(int i=0;i<20;i++){now=130000;dwc2_diag_disable_decision(&h,&e,0x80000000);}assert(h.irq_diag.sample_count==8&&h.irq_diag.early_count==8&&h.irq_diag.selected_early==20);
 memset(&h,0,sizeof(h));h.gadget.speed=USB_SPEED_HIGH;snapshot(&h,16383,99000,0);snapshot(&h,0,126000,GINTSTS_INCOMPL_SOIN);e.target_frame=0;dwc2_diag_disable_decision(&h,&e,0x80000000);assert(h.irq_diag.selected_early==1);
 puts("11 actual-source sampling scenarios passed (synthetic MMIO and clock).");
}
'''
with tempfile.TemporaryDirectory(prefix='pisight-irq-sampling-') as tmp:
    epoch=extract('dwc2_isoc_epoch_valid') if 'static bool dwc2_isoc_epoch_valid(' in source else ''
    p=Path(tmp); (p/'test.c').write_text(prefix+epoch+extract('dwc2_diag_irq_snapshot')+extract('dwc2_diag_disable_decision')+tests)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(root),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True,timeout=10)
