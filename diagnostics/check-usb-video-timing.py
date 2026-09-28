#!/usr/bin/env python3
"""Run the gadget's endpoint setup and the built kernel's descriptor logic.

Usage: check-usb-video-timing.py UVC_GADGET_SH F_UVC_C [SHELL]
This verifies the proposed USB configuration, not physical USB timing.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

script = Path(sys.argv[1]).read_text()
kernel = Path(sys.argv[2]).read_text()
shell = sys.argv[3:] or ["/bin/sh"]
start = script.index("\t# This configures the USB endpoint")
end = script.index("\n\tln -s functions/$FUNCTION", start)
setup = script[start:end]
start = kernel.index("\t/* Sanity check the streaming endpoint module parameters. */")
end = kernel.index("\n\t/* Allocate endpoints. */", start)
descriptor_logic = kernel[start:end]

with tempfile.TemporaryDirectory(prefix="pisight-usb-timing-") as directory:
    work = Path(directory)
    endpoint = work / "functions/uvc.0"
    endpoint.mkdir(parents=True)
    # Configfs's defaults from f_uvc.c; the setup code must override them.
    (endpoint / "streaming_maxpacket").write_text("1024\n")
    (endpoint / "streaming_interval").write_text("1\n")
    subprocess.run(shell + ["-e", "-c", "FUNCTION=uvc.0\n" + setup],
                   cwd=work, check=True)
    packet = int((endpoint / "streaming_maxpacket").read_text())
    interval = int((endpoint / "streaming_interval").read_text())
    source = work / "descriptor.c"
    source.write_text(r'''
#include <stdio.h>
#include <stdlib.h>
#define min(a,b) ((a)<(b)?(a):(b))
#define clamp(v,lo,hi) ((v)<(lo)?(lo):min(v,hi))
#define roundup(v,n) (((v)+(n)-1)/(n)*(n))
#define cpu_to_le16(v) (v)
#define uvcg_info(...) ((void)0)
struct options { unsigned streaming_interval, streaming_maxpacket, streaming_maxburst; };
struct endpoint { unsigned wMaxPacketSize, bInterval; };
struct companion { unsigned bmAttributes, bMaxBurst, wBytesPerInterval; };
int main(int argc, char **argv) {
    struct options values = {atoi(argv[2]), atoi(argv[1]), 0}, *opts = &values;
    struct endpoint uvc_fs_streaming_ep, uvc_hs_streaming_ep, uvc_ss_streaming_ep;
    struct companion uvc_ss_streaming_comp;
    unsigned max_packet_mult, max_packet_size;
''' + descriptor_logic + r'''
    printf("%u %u\n", uvc_hs_streaming_ep.wMaxPacketSize, uvc_hs_streaming_ep.bInterval);
}
''')
    binary = work / "descriptor"
    subprocess.run(["cc", "-std=c99", str(source), "-o", str(binary)], check=True)

    def resolve(maxpacket, binterval):
        return tuple(map(int, subprocess.check_output(
            [str(binary), str(maxpacket), str(binterval)], text=True).split()))

    # Guard against the ineffective "change interval only" approach.
    assert resolve(2048, 2) == (3072, 1), "Kernel high-bandwidth rule changed"
    encoded_packet, actual_interval = resolve(packet, interval)
    transactions = 1 + ((encoded_packet >> 11) & 3)
    bytes_per_service = (encoded_packet & 2047) * transactions
    services_per_second = 8000 // (1 << (actual_interval - 1))
    payload_per_second = (bytes_per_service - 12) * services_per_second
    result = dict(config_maxpacket=packet, config_interval=interval,
                  hs_wMaxPacketSize=encoded_packet, hs_bInterval=actual_interval,
                  transactions=transactions, services_per_second=services_per_second,
                  payload_bytes_per_second=payload_per_second,
                  payload_bytes_per_30fps_frame=payload_per_second // 30)
    print(json.dumps(result, indent=2))
    assert (bytes_per_service, actual_interval) == (1024, 2), \
        "Video still requires 125-us service; expected one 1024-byte packet per 250 us"
    assert payload_per_second >= 3 * 42546 * 30, "Insufficient measured-720p headroom"
    print("PASS: real setup plus kernel descriptor mapping; hardware result pending")
