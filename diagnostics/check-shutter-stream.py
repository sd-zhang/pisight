#!/usr/bin/env python3
"""Exercise production stream event functions; stub camera start/stop and LED I/O.

Extract functions verbatim so this runs on macOS without Linux V4L2 headers.
The full ARM build separately checks header and call-site integration.
"""
import pathlib
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1])
text = (source / 'lib/stream.c').read_text()

def block(marker):
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

functions = ['static void uvc_stream_update_leds', 'void uvc_stream_set_logo_mode',
             'void uvc_stream_enable', 'void uvc_stream_set_gpio_callback']
if 'void uvc_stream_set_shutter_closed' in text:
    functions.append('void uvc_stream_set_shutter_closed')
code = '''
#include <assert.h>
#include <stdio.h>
#include "gpio.h"
typedef int (*uvc_stream_gpio_cb_t)(void *, int, int);
#define uvc_log(...) ((void)0)
static int uvc_dbg_first_frame;
'''
code += block('struct uvc_stream\n{') + ';\n'
code += '''
static int starts, stops, writes, levels[2], start_fail;
static int uvc_stream_start(struct uvc_stream *s) { (void)s; starts++; return start_fail ? -1 : 0; }
static void uvc_stream_stop(struct uvc_stream *s) { (void)s; stops++; }
static int led(void *data, int pin, int state) {
    assert(data == levels);
    assert(pin == RUNNING || pin == STREAMING);
    assert(state == 0 || state == 1);
    levels[pin] = state;
    writes++;
    return 0;
}
'''
code += '\n'.join(block(name) for name in functions)
if 'void uvc_stream_set_shutter_closed' not in text:
    code += 'void uvc_stream_set_shutter_closed(struct uvc_stream *s, int c) { (void)s; (void)c; }\n'
code += r'''
int main(void) {
    struct uvc_stream s = {0};
    uvc_stream_set_gpio_callback(&s, led, levels);
    uvc_stream_enable(&s, 1);
    assert(starts == 1 && stops == 0);
    uvc_stream_set_shutter_closed(&s, 1);
    assert(stops == 1 && !s.active && !levels[STREAMING]);
    uvc_stream_enable(&s, 1); // Queued/host start while shutter closed.
    assert(starts == 1 && !s.active);
    uvc_stream_enable(&s, 0); // Kernel disconnect and later STREAMOFF duplicates.
    uvc_stream_enable(&s, 0);
    assert(stops == 1);
    uvc_stream_set_shutter_closed(&s, 0);
    assert(starts == 1); // Reopening waits for the host to request capture.
    uvc_stream_enable(&s, 1);
    assert(starts == 2 && s.active);
    uvc_stream_enable(&s, 1);
    assert(starts == 2);
    uvc_stream_enable(&s, 0);
    assert(stops == 2 && !s.active);
    start_fail = 1;
    uvc_stream_enable(&s, 1); // A failed start may still own buffers/source state.
    uvc_stream_set_shutter_closed(&s, 1);
    assert(stops == 3 && !s.active);
    uvc_stream_enable(&s, 0);
    assert(stops == 3);
    puts("PASS: shutter stops capture, blocks queued starts, and resumes only on host request");
}
'''
with tempfile.TemporaryDirectory(prefix='pisight-shutter-stream-') as directory:
    work = pathlib.Path(directory)
    (work / 'check.c').write_text(code)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(source / 'include/uvcgadget'), str(work / 'check.c'),
                    '-o', str(work / 'check')], check=True)
    subprocess.run([str(work / 'check')], check=True)
