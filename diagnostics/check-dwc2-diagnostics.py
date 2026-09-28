#!/usr/bin/env python3
"""Compile the actual diagnostic helper; this does not emulate USB hardware."""
import pathlib
import re
import subprocess
import sys
import tempfile

root = pathlib.Path(sys.argv[1])
header = (root / 'drivers/usb/dwc2/core.h').read_text()
source = (root / 'drivers/usb/dwc2/gadget.c').read_text()

def block(text, start):
    pos = text.index(start)
    opening = text.index('{', pos)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[pos:end]

types = '\n'.join(block(header, f'struct {name} {{') + ';' for name in
                  ('dwc2_isoc_diag_sample', 'dwc2_isoc_diag'))
helper = block(source, 'static void dwc2_isoc_diag_miss(')
for name, reason in [('dwc2_hsotg_start_req', 0),
                     ('dwc2_gadget_handle_ep_disabled', 1),
                     ('dwc2_gadget_handle_out_token_ep_disabled', 2),
                     ('dwc2_gadget_handle_nak', 3)]:
    body = block(source, f'static void {name}(')
    assert re.search(rf'dwc2_isoc_diag_miss\([^,]+, {reason},', body), name
    assert body.index('dwc2_isoc_diag_miss(') < body.index('-ENODATA'), name
assert 'hs_ep->diag_sessions++' in source
assert 'memset(hs_ep->isoc_diag' not in source, 'short sessions must remain observable'

test = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
typedef uint64_t u64;
TYPES
struct dwc2_hsotg { u32 frame_number; };
struct usb_request { unsigned length; };
struct dwc2_hsotg_req { struct usb_request req; };
struct dwc2_hsotg_ep {
 struct dwc2_hsotg *parent;
 struct dwc2_isoc_diag isoc_diag[4];
 u32 target_frame, diag_irq, diag_sessions;
 bool frame_overrun;
};
static u32 live;
static unsigned clock_reads;
static u32 dwc2_hsotg_read_frameno(struct dwc2_hsotg *hs) {
 (void)hs; ++clock_reads; return live;
}
static u64 ktime_get_ns(void) { return 1234567890; }
HELPER
int main(void) {
 struct dwc2_hsotg hs = {.frame_number=0x3ff9};
 struct dwc2_hsotg_ep ep = {.parent=&hs,.target_frame=0,
   .frame_overrun=true,.diag_irq=3,.diag_sessions=2};
 struct dwc2_hsotg_req req = {.req.length=2048};
 live=0x3ffa;
 for (unsigned i=1; i<=16384; ++i) {
   dwc2_isoc_diag_miss(&ep, 1, i, &req);
   ep.target_frame++;
 }
 struct dwc2_isoc_diag *d=&ep.isoc_diag[1];
 assert(d->missed==16384 && d->payload==16384 && d->max_burst==16384);
 assert(clock_reads==1); /* No clock read per expired request in a storm. */
 assert(d->worst.target==0 && d->worst.cached==0x3ff9);
 assert(d->worst.live==0x3ffa && d->worst.overrun && d->worst.irq==3);
 assert(d->worst.ns==1234567890 && d->first.target==0);
 assert(d->worst.session==2);
 req.req.length=0; ep.target_frame=100; hs.frame_number=101; live=102;
 dwc2_isoc_diag_miss(&ep, 1, 1, &req);
 assert(d->missed==16385 && d->payload==16384);
 assert(d->last.target==100 && d->worst.target==0 && d->first.target==0);
 for(unsigned reason=0; reason<4; ++reason)
   if(reason!=1) {
     dwc2_isoc_diag_miss(&ep, reason, 1, &req);
     assert(ep.isoc_diag[reason].missed==1);
     assert(ep.isoc_diag[reason].payload==0);
   }
 ep.target_frame=200;
 for(unsigned i=1; i<=16385; ++i)
   dwc2_isoc_diag_miss(&ep, 1, i, &req);
 assert(d->max_burst==16385 && d->worst.target==200);
 assert(d->first.target==0);
 puts("PASS: per-path counts, bounded burst sampling, first/last/worst evidence");
}
'''.replace('TYPES', types).replace('HELPER', helper)
with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / 'probe.c'
    path.write_text(test)
    binary = pathlib.Path(tmp) / 'probe'
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                    str(path), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
