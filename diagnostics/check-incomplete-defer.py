#!/usr/bin/env python3
"""Exercise production incomplete-IN selection against clock/MMIO fixtures.

The first fixture comes from the Pi's captured early retirement. Hardware
interrupt assertion is supplied as an input, not claimed to be emulated.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
source = (root / 'gadget.c').read_text()
header = (root / 'isoc-diag.h').read_text()
# Backward-compatible fake storage lets the same behavioral test run on the
# uncorrected source. No production function is rewritten by this test.
if 'recovery_epoch' not in header:
    header = header.replace('struct dwc2_irq_diag {', '''struct dwc2_irq_diag {
 u32 recovery_epoch, deferred, deferred_completed, deferred_recovered;''')


def extract(name, optional=False):
    m = re.search(r'^static (?:inline )?\w+ ' + name + r'\([^;]+?\)\n\{', source, re.M)
    if not m:
        if optional:
            return ''
        raise ValueError(name)
    pos, depth = m.end(), 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[m.start():pos]


prefix = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32; typedef uint16_t u16; typedef uint64_t u64;
'''+header+r'''
#define BIT(n) (1u << (n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define USB_SPEED_HIGH 3
#define DWC2_L0 0
#define DSTS_SOFFN_LIMIT 0x3fff
#define DSTS_SOFFN_MASK (0x3fff << 8)
#define DSTS_SOFFN_SHIFT 8
#define DSTS_SUSPSTS 1
#define DSTS_ERRATICERR 8
#define DSTS 0
#define DCFG 1
#define GINTSTS 2
#define DAINTMSK 3
#define DIEPCTL(n) (4+(n))
#define DIEPINT(n) (20+(n))
#define DIEPTSIZ(n) (36+(n))
#define DXEPCTL_EPENA BIT(31)
#define DXEPCTL_EPDIS BIT(30)
#define DXEPCTL_SNAK BIT(27)
#define GINTSTS_MODEMIS BIT(1)
#define GINTSTS_USBRST BIT(12)
#define GINTSTS_RESETDET BIT(23)
#define GINTSTS_ENUMDONE BIT(13)
#define GINTSTS_USBSUSP BIT(11)
#define GINTSTS_WKUPINT BIT(31)
#define GINTSTS_DISCONNINT BIT(29)
#define GINTSTS_CONIDSTSCHNG BIT(28)
#define GINTSTS_IEPINT BIT(18)
#define GINTSTS_OEPINT BIT(19)
#define GINTSTS_INCOMPL_SOIN BIT(20)
#define dev_dbg(...) ((void)0)
struct dwc2_hsotg;
struct dwc2_hsotg_ep {
 struct dwc2_hsotg *parent;
 unsigned index, target_frame, diag_sessions;
 bool frame_overrun, isochronous;
 void *req;
 struct dwc2_diag_arm diag_arm;
 struct {u64 ns; u32 serial, session, target, epoch; bool valid;} deferred;
};
struct dwc2_hsotg {
 struct dwc2_irq_diag irq_diag;
 struct {int speed;} gadget;
 int lx_state; bool bus_suspended, dma, ddma;
 u32 frame_number, num_of_eps;
 struct dwc2_hsotg_ep *eps_in[4];
};
static u32 regs[52]; static u64 now, ack_delay;
static bool event_during_scan, event_at_ack, event_after_ack;
static unsigned transition_during_decision;
static unsigned ack_count, failures, cases;
static u64 ktime_get_ns(void) {return now;}
static u32 dwc2_readl(struct dwc2_hsotg *h, u32 r) {
 (void)h;
 if(r==DIEPINT(1) && transition_during_decision) {
  if(transition_during_decision==1)regs[GINTSTS]|=GINTSTS_USBRST;
  if(transition_during_decision==2)regs[GINTSTS]|=GINTSTS_MODEMIS;
  if(transition_during_decision==3)regs[GINTSTS]|=GINTSTS_CONIDSTSCHNG;
  if(transition_during_decision==4)regs[DSTS]|=DSTS_ERRATICERR;
  transition_during_decision=0;
 }
 if(r==DIEPCTL(3) && event_during_scan) {
  now += 60000; regs[GINTSTS] |= GINTSTS_INCOMPL_SOIN;
  event_during_scan=false;
 }
 return regs[r];
}
static void dwc2_writel(struct dwc2_hsotg *h, u32 v, u32 r) {
 (void)h;
 if(r==GINTSTS) {
  now+=ack_delay;
  if(event_at_ack)regs[r]|=GINTSTS_INCOMPL_SOIN;
  regs[r]&=~v;
  if(event_after_ack)regs[r]|=GINTSTS_INCOMPL_SOIN;
  ack_count++;
 }
 else regs[r]=v;
}
static bool using_dma(struct dwc2_hsotg *h) {return h->dma;}
static bool using_desc_dma(struct dwc2_hsotg *h) {return h->ddma;}
'''

tests = r'''
static struct dwc2_hsotg h;
static struct dwc2_hsotg_ep eps[4];
static void snapshot(u32 frame, u64 ns, u32 status) {
 regs[DSTS]=frame<<8; h.frame_number=frame; now=ns;
 dwc2_diag_irq_snapshot(&h,status,~0u);
}
static void prepare(u32 frame) {
 memset(&h,0,sizeof(h)); memset(eps,0,sizeof(eps)); memset(regs,0,sizeof(regs));
 h.gadget.speed=USB_SPEED_HIGH; h.dma=true; h.num_of_eps=4;
 for(unsigned i=0;i<4;i++){eps[i].parent=&h;eps[i].index=i;h.eps_in[i]=&eps[i];}
 eps[1].target_frame=frame; eps[1].isochronous=true; eps[1].req=&eps[1];
 eps[1].diag_sessions=1; eps[1].diag_arm.serial=95303;
 eps[1].diag_arm.target=frame;
 eps[1].diag_arm.before_frame=eps[1].diag_arm.after_frame=(frame-1)&0x3fff;
 eps[1].diag_arm.length=2048;
 eps[3].target_frame=(frame+7)&0x3fff; eps[3].frame_overrun=frame>16376;
 eps[3].isochronous=true; eps[3].req=&eps[3];
 regs[DAINTMSK]=BIT(1)|BIT(3); regs[DIEPCTL(1)]=regs[DIEPCTL(3)]=DXEPCTL_EPENA;
 regs[DIEPTSIZ(1)]=0x40100000; regs[DIEPINT(1)]=0x10;
 regs[DCFG]=0x4040150;
 ack_delay=ack_count=0; event_during_scan=event_at_ack=event_after_ack=false;
 transition_during_decision=0;
 snapshot((frame-1)&0x3fff,80632345000ull,0);
 snapshot(frame,80632397000ull,GINTSTS_INCOMPL_SOIN);
 regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;
}
static void expect(const char *name, bool ok) {
 printf("%s %s\n",ok?"PASS":"FAIL",name); failures+=!ok; cases++;
}
static bool disabled(unsigned ep){return !!(regs[DIEPCTL(ep)]&DXEPCTL_EPDIS);}
static void handle(void){dwc2_gadget_handle_incomplete_isoc_in(&h);}
int main(void) {
 prepare(12913);handle();
 expect("recorded early video survives old global cause", !disabled(1)&&!disabled(3)&&!regs[GINTSTS]);
 prepare(12913);event_during_scan=true;handle();
 expect("later genuine EOPF remains pending after scan", !disabled(1)&&(regs[GINTSTS]&GINTSTS_INCOMPL_SOIN)&&ack_count==1);
 prepare(12913);ack_delay=60000;handle();
 expect("ack crossed bound falls back to recovery",disabled(1));
 prepare(12913);ack_delay=60000;event_at_ack=true;handle();
 expect("genuine EOPF coalesced before W1C gets normal recovery",disabled(1));
 prepare(12913);ack_delay=60000;event_after_ack=true;handle();
 expect("genuine EOPF after W1C stays pending and recovers",disabled(1)&&(regs[GINTSTS]&GINTSTS_INCOMPL_SOIN));
 prepare(12913);event_after_ack=true;handle();
 expect("unexplained reassertion rejects early attribution",disabled(1));
 prepare(12913);now+=60000;handle();
 expect("late observation uses normal recovery",disabled(1));
 prepare(12913);regs[GINTSTS]|=GINTSTS_USBRST;handle();
 expect("pending reset rejects early proof",disabled(1));
 prepare(12913);h.bus_suspended=true;handle();
 expect("suspend rejects early proof",disabled(1));
 prepare(12913);h.ddma=true;handle();
 expect("descriptor DMA never uses deferral",disabled(1));
 prepare(12913);h.dma=false;handle();
 expect("slave mode never uses deferral",disabled(1));
 prepare(12913);eps[1].target_frame=12912;handle();
 expect("already expired target recovers immediately",disabled(1));
 prepare(12913);regs[DIEPCTL(1)]=0;handle();
 expect("completed endpoint is not disabled",!disabled(1));
 prepare(12913);eps[1].req=NULL;handle();
 expect("missing active request cannot be deferred",disabled(1));
 prepare(12913);handle();
 snapshot(12913,80632480000ull,GINTSTS_INCOMPL_SOIN);regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;handle();
 expect("genuine later same-frame EOPF recovers",disabled(1));
 prepare(16383);handle();regs[DIEPCTL(1)]=DXEPCTL_EPENA;
 snapshot(0,80632530000ull,GINTSTS_INCOMPL_SOIN);regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;handle();
 expect("deferred last frame recovers after counter wrap without NAK",disabled(1));
 prepare(16383);handle();regs[DIEPCTL(1)]=DXEPCTL_EPENA;
 snapshot(16383,82680397000ull,GINTSTS_INCOMPL_SOIN);regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;handle();
 expect("identical request after full counter wrap recovers",disabled(1));
 prepare(16383);handle();regs[DIEPCTL(1)]=DXEPCTL_EPENA;
 snapshot(8192,83704397000ull,GINTSTS_INCOMPL_SOIN);regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;handle();
 expect("elapsed timestamp resolves ambiguous half-counter age",disabled(1));
 for(unsigned transition=1;transition<=4;transition++) {
  prepare(16383);handle();regs[DIEPCTL(1)]=DXEPCTL_EPENA;
  snapshot(0,80632530000ull,GINTSTS_INCOMPL_SOIN);regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;
  transition_during_decision=transition;handle();
  expect("new epoch transition during decision cancels forced wrap recovery",!disabled(1));
 }
 /* New-arm identity must not inherit authorization across wrap. Original
  * comparison regards target16383 as future at0; only a stale record could
  * incorrectly authorize it in these fixtures. */
 for(unsigned mutation=0;mutation<4;mutation++) {
  prepare(16383);handle();regs[DIEPCTL(1)]=DXEPCTL_EPENA;
  if(mutation==0)eps[1].diag_arm.serial++;
  if(mutation==1)eps[1].diag_sessions++;
  if(mutation==2)h.irq_diag.recovery_epoch++;
  if(mutation==3)eps[1].req=NULL;
  snapshot(0,80632530000ull,GINTSTS_INCOMPL_SOIN);regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;handle();
  expect("changed request/session/epoch has no deferred ownership",!disabled(1));
 }
 printf("%u cases, %u failures; synthetic MMIO, not hardware validation.\n",cases,failures);
 return failures?1:0;
}
'''

names = ['dwc2_diag_irq_snapshot', 'dwc2_diag_disable_decision',
         'dwc2_gadget_target_frame_elapsed']
functions = extract('dwc2_isoc_epoch_valid', optional=True)
functions += '\n' + '\n'.join(extract(n) for n in names)
functions += '\n' + extract('dwc2_isoc_deferred_matches', optional=True)
functions += '\n' + extract('dwc2_isoc_deferred_elapsed', optional=True)
functions += '\n' + extract('dwc2_isoc_ack_before_eopf', optional=True)
functions += '\n' + extract('dwc2_gadget_handle_incomplete_isoc_in')
with tempfile.TemporaryDirectory(prefix='pisight-incomplete-defer-') as tmp:
    p = Path(tmp)
    (p/'test.c').write_text(prefix+functions+tests)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                    '-fsanitize=undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    result = subprocess.run([str(p/'test')],timeout=10)
    sys.exit(result.returncode)
