#!/usr/bin/env python3
"""Exercise the built driver's incomplete-IN endpoint selection on native C.

This is a control-flow experiment, not a USB hardware/timing emulator. In the
delayed-event case, the origin of the pending interrupt is an explicit input
assumption. The existing Pi logs do not establish that assumption.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).read_text()


def extract(name):
    match = re.search(r"^static \w+ " + name + r"\([^;]+?\)\n\{", source, re.M)
    if not match:
        raise ValueError(f"Cannot find {name}")
    pos, depth = match.end(), 1
    while depth:
        depth += (source[pos] == "{") - (source[pos] == "}")
        pos += 1
    return source[match.start():pos]


prefix = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
typedef uint16_t u16;
#define USB_SPEED_HIGH 3
#define DSTS_SOFFN_LIMIT 0x3fff
#define BIT(n) (1u << (n))
#define DXEPCTL_EPENA BIT(31)
#define DXEPCTL_EPDIS BIT(30)
#define DXEPCTL_SNAK BIT(27)
#define GINTSTS_INCOMPL_SOIN BIT(20)
#define DAINTMSK 0
#define GINTSTS 1
#define DIEPCTL(i) (2 + (i))
#define dev_dbg(...) ((void)0)
struct dwc2_hsotg;
struct dwc2_hsotg_ep {
    struct dwc2_hsotg *parent;
    u32 target_frame;
    bool frame_overrun, isochronous;
};
struct dwc2_hsotg {
    struct { u32 waiting[16]; } irq_diag;
    struct { int speed; } gadget;
    u32 frame_number, num_of_eps;
    struct dwc2_hsotg_ep *eps_in[4];
};
/* Diagnostic observer stub: selection policy is the subject of this replay. */
static void __attribute__((unused)) dwc2_diag_disable_decision(struct dwc2_hsotg *h,
    struct dwc2_hsotg_ep *e, u32 ctrl) { (void)h; (void)e; (void)ctrl; }
static u32 regs[6];
static u32 dwc2_readl(struct dwc2_hsotg *h, u32 r) { (void)h; return regs[r]; }
static void dwc2_writel(struct dwc2_hsotg *h, u32 v, u32 r) {
    (void)h;
    /* GINTSTS is write-one-to-clear; endpoint writes are recorded, not
     * executed by an emulated controller. */
    if (r == GINTSTS) regs[r] &= ~v;
    else regs[r] = v;
}
'''

tests = r'''
static unsigned cases;
static void run(const char *name, unsigned now, unsigned video_target,
                bool video_wrap, unsigned audio_target, bool audio_wrap,
                bool video_enabled, bool video_masked, bool video_iso,
                unsigned expected_disabled) {
    struct dwc2_hsotg h = {.gadget.speed=USB_SPEED_HIGH,
                           .frame_number=now, .num_of_eps=4};
    struct dwc2_hsotg_ep eps[4] = {0};
    memset(regs, 0, sizeof(regs));
    for (unsigned i=0; i<4; i++) { eps[i].parent=&h; h.eps_in[i]=&eps[i]; }
    eps[1].isochronous=video_iso; eps[1].target_frame=video_target;
    eps[1].frame_overrun=video_wrap;
    eps[3].isochronous=true; eps[3].target_frame=audio_target;
    eps[3].frame_overrun=audio_wrap;
    regs[DAINTMSK]=BIT(3) | (video_masked ? 0 : BIT(1));
    regs[GINTSTS]=GINTSTS_INCOMPL_SOIN;
    regs[DIEPCTL(1)]=video_enabled ? DXEPCTL_EPENA : 0;
    regs[DIEPCTL(3)]=DXEPCTL_EPENA;
    dwc2_gadget_handle_incomplete_isoc_in(&h);
    unsigned disabled=0;
    for (unsigned i=1; i<4; i++)
        if (regs[DIEPCTL(i)] & DXEPCTL_EPDIS) disabled |= BIT(i);
    if (disabled != expected_disabled || regs[GINTSTS]) {
        fprintf(stderr, "Unexpected replay result: %s mask=%x\n", name, disabled);
        exit(1);
    }
    printf("%s: video_disable=%u audio_disable=%u global_cleared=1\n",
           name, !!(disabled & BIT(1)), !!(disabled & BIT(3)));
    cases++;
}
int main(void) {
    /* Audio is armed for 108 while video is armed for 101. A current-frame
     * audio incomplete event at 100 must leave both future targets alone. */
    run("prompt_audio_event",100,101,false,108,false,true,false,true,0);
    /* Assume the same event latched at 100 is serviced at the beginning of
     * 101, before that frame's video token. There is no event-frame input
     * to this handler: it disables the still-pending video request. */
    run("assumed_delayed_audio_event",101,101,false,108,false,true,false,true,BIT(1));
    /* At the end of 101, a genuinely missed video transfer has identical
     * observable inputs and gets exactly the same endpoint selection. */
    run("genuine_video_miss",101,101,false,108,false,true,false,true,BIT(1));
    run("both_expired",108,108,false,108,false,true,false,true,BIT(1)|BIT(3));
    run("video_already_completed",101,101,false,108,false,false,false,true,0);
    run("video_masked",101,101,false,108,false,true,true,true,0);
    run("nonisoc_video",101,101,false,108,false,true,false,false,0);
    run("prompt_before_wrap",16383,0,true,6,true,true,false,true,0);
    run("assumed_delayed_across_wrap",0,0,true,6,true,true,false,true,BIT(1));
    printf("%u control-flow cases matched; hardware event timing NOT tested.\n", cases);
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix="pisight-incomplete-") as directory:
    path = Path(directory)
    code = path / "replay.c"
    code.write_text(prefix + "\n".join(extract(name) for name in (
        "dwc2_gadget_target_frame_elapsed",
        "dwc2_gadget_handle_incomplete_isoc_in")) + tests)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=undefined", str(code), "-o", str(path / "replay")], check=True)
    subprocess.run([str(path / "replay")], check=True, timeout=10)
