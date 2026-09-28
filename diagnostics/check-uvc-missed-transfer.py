#!/usr/bin/env python3
"""Exercise the built UVC completion status switch with simulated requests.

Usage: python3 check-uvc-missed-transfer.py path/to/uvc_video.c
This verifies error classification, not physical USB timing or image integrity.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).read_text()
start = source.index("switch (req->status)", source.index("uvc_video_complete("))
brace = source.index("{", start)
depth = 1
end = brace + 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
switch = source[start:end]
code = r'''
#include <stdio.h>
#define EXDEV 18
#define ENODATA 61
#define ESHUTDOWN 108
#define EIO 5
#define UVC_QUEUE_DROP_INCOMPLETE 1
#define uvcg_dbg(...) ((void)0)
#define uvcg_warn(...) ((void)0)
struct queue { int flags, cancelled, disconnected; };
struct request { int status, length; };
static void uvcg_queue_cancel(struct queue *q, int disconnect) {
    q->cancelled++; q->disconnected = disconnect;
}
static void complete(struct queue *queue, struct request *req) {
''' + switch + r'''
}
int main(void) {
    const int cases[][5] = {
        /* status, length, incomplete, cancellations, disconnected */
        {0, 2048, 0, 0, 0},
        {-EXDEV, 2048, 1, 0, 0},
        {-EXDEV, 0, 0, 0, 0},
        {-ENODATA, 2048, 1, 0, 0},
        {-ENODATA, 0, 0, 0, 0},
        {-ESHUTDOWN, 2048, 0, 1, 1},
        {-EIO, 2048, 0, 1, 0},
    };
    int failures = 0;
    for (unsigned i = 0; i < sizeof(cases)/sizeof(cases[0]); i++) {
        struct queue q = {0};
        struct request req = {cases[i][0], cases[i][1]};
        complete(&q, &req);
        int ok = q.flags == cases[i][2] && q.cancelled == cases[i][3]
            && q.disconnected == cases[i][4];
        printf("%s status=%d length=%d incomplete=%d cancelled=%d disconnected=%d\n",
               ok ? "PASS" : "FAIL", req.status, req.length,
               q.flags, q.cancelled, q.disconnected);
        failures += !ok;
    }
    return !!failures;
}
'''
with tempfile.TemporaryDirectory(prefix="pisight-uvc-status-") as tmp:
    c = Path(tmp) / "check.c"
    binary = Path(tmp) / "check"
    c.write_text(code)
    subprocess.run(["cc", "-Wall", "-Wextra", "-Werror", str(c), "-o", str(binary)], check=True)
    sys.exit(subprocess.run([str(binary)]).returncode)
