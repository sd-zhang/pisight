#!/usr/bin/env python3
"""Reject a tempting recovery change; synthetic next-poll NAK, not hardware proof.
Actual code must recover all four cases. The strict-past experiment must expose
both frame-wrap failures; those expected failures reject it as a candidate.
"""
from pathlib import Path
import ast, re, subprocess
repo=Path(__file__).resolve().parent.parent
model=ast.parse((repo/'diagnostics/check-dwc2-coalesced.py').read_text())
values={}
for node in model.body:
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('prefix','names'):
        values[node.targets[0].id]=ast.literal_eval(node.value)
source=Path('/private/tmp/pisight-coalesced-fix/new/drivers/usb/dwc2/gadget.c').read_text()
def extract(name):
    m=re.search(r'^static (?:inline )?\w+ '+name+r'\([^;]+?\)\n\{',source,re.M)
    pos=m.end();depth=1
    while depth:
        depth+=(source[pos]=='{')-(source[pos]=='}');pos+=1
    body=source[m.start():pos]
    if name=='dwc2_hsotg_epint':body=body.split('\n\tif (ints & DXEPINT_AHBERR)')[0]+'\n}'
    return body
prefix=values['prefix'].replace('static u32 regs[7]','static u32 regs[10]').replace('struct dwc2_hsotg_ep *ep;','struct dwc2_hsotg_ep *ep; unsigned num_of_eps; struct dwc2_hsotg_ep *eps_in[2];')
prefix+='\n#define BIT(n) (1u<<(n))\n#define DAINTMSK 7\n#define GINTSTS 8\n#define GINTSTS_INCOMPL_SOIN (1u<<20)\n#define DXEPCTL_EPDIS (1u<<30)\n#define DXEPCTL_SNAK (1u<<27)\n'
funcs='\n'.join(extract(n) for n in values['names'])
incomplete=extract('dwc2_gadget_handle_incomplete_isoc_in')
strict=incomplete.replace('dwc2_gadget_target_frame_elapsed(hs_ep))', 'hs_ep->target_frame != hsotg->frame_number &&\n\t\t    dwc2_gadget_target_frame_elapsed(hs_ep))')
assert strict!=incomplete
main=r'''
static unsigned failed;
static void run(unsigned interval,unsigned frame) {
 struct dwc2_hsotg h={.gadget.speed=USB_SPEED_HIGH,.params.g_dma=1,.frame_number=frame,.num_of_eps=2};
 struct dwc2_hsotg_ep e={.parent=&h,.target_frame=frame,.interval=interval,.index=1,.dir_in=1,.isochronous=1,.size_loaded=96};
 struct dwc2_hsotg_req reqs[2]={0}; h.ep=&e;h.eps_in[1]=&e;init(&e.queue);
 memset(regs,0,sizeof(regs)); regs[DAINTMSK]=BIT(1);regs[2]=DXEPCTL_EPENA;
 live=frame; requeue=1;starts=flushes=flush_after_start=givebacks=0;
 for(int i=0;i<2;i++){reqs[i].id=i+1;reqs[i].req.length=96;reqs[i].req.status=-EINPROGRESS;reqs[i].req.complete=(void*)1;append(&reqs[i].queue,&e.queue);}
 e.req=&reqs[0];
 dwc2_gadget_handle_incomplete_isoc_in(&h);
 bool disabled=!!(regs[2]&DXEPCTL_EPDIS);
 if(disabled){regs[2]=0;irq=DXEPINT_EPDISBLD;dwc2_hsotg_epint(&h,1,1);}
 /* Genuine failed transfer: assume hardware next emits NAK at next host poll.
  * The assumption is tested for driver behavior only, not HW feasibility. */
 live=(frame+interval)&DSTS_SOFFN_LIMIT;h.frame_number=live;irq=DXEPINT_NAKINTRPT;
 dwc2_hsotg_epint(&h,1,1);
 if(givebacks!=2||starts!=1||statuses[0]!=-ENODATA||statuses[1]!=-ENODATA||e.target_frame!=((frame+2*interval)&DSTS_SOFFN_LIMIT)) {printf("REJECT interval=%u frame=%u callbacks=%d starts=%d target=%u\n",interval,frame,givebacks,starts,e.target_frame);failed++;return;}
 live=e.target_frame;h.frame_number=live;irq=DXEPINT_XFERCOMPL;regs[4]=0;
 dwc2_hsotg_epint(&h,1,1);
 if(givebacks!=3||statuses[2]!=0||starts!=2)abort();
 printf("interval=%u frame=%u initial_disable=%u missed=2 next_complete=success\n",interval,frame,disabled);
}
int main(void){run(1,100);run(8,104);run(1,16383);run(8,16376);return failed;}
'''
for label,handler in [('actual',incomplete),('strict_past_experiment',strict)]:
    code=Path('/private/tmp')/('pisight-'+label+'.c');exe=code.with_suffix('')
    code.write_text(prefix+funcs+handler+main)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable','-fsanitize=undefined',str(code),'-o',str(exe)],check=True)
    print(label,flush=True)
    result=subprocess.run([str(exe)],timeout=10)
    assert result.returncode == (0 if label=='actual' else 2),result.returncode

print("Actual recovery passed; strict-past candidate rejected by two wrap cases.")
