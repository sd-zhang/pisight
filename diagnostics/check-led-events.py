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
static int starts, stops, writes, levels[2];
static int uvc_stream_start(struct uvc_stream *s) { (void)s; starts++; return 0; }
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
code += '''
int main(void) {
    for (unsigned int mode = 0; mode < 3; mode++) {
        struct uvc_stream s = {0};
        uvc_stream_set_logo_mode(&s, mode);
        int before = writes;
        uvc_stream_set_gpio_callback(&s, led, levels);
        assert(writes == before + 2);
        assert(levels[RUNNING] == (mode == 1) && !levels[STREAMING]);
        for (int cycle = 0; cycle < 3; cycle++) {
            uvc_stream_enable(&s, 1);
            assert(levels[RUNNING] == (mode != 0) && levels[STREAMING]);
            uvc_stream_enable(&s, 0);
            assert(levels[RUNNING] == (mode == 1) && !levels[STREAMING]);
        }
        // Live settings must work both while streaming and while idle.
        for (int active = 0; active < 2; active++) {
            uvc_stream_enable(&s, active);
            for (unsigned int live = 0; live < 3; live++) {
                uvc_stream_set_logo_mode(&s, live);
                assert(levels[RUNNING] == (live == 1 || (live == 2 && active)));
                assert(levels[STREAMING] == active);
            }
        }
        before = writes;
        uvc_stream_set_gpio_callback(&s, NULL, NULL);
        uvc_stream_enable(&s, 0);
        assert(writes == before);
    }
    assert(starts == 12 && stops == 12);
    puts("PASS: all logo modes at boot, stream cycles, live settings and no GPIO");
}
'''
with tempfile.TemporaryDirectory(prefix='pisight-led-events-') as directory:
    work = pathlib.Path(directory)
    (work / 'check.c').write_text(code)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(source / 'include/uvcgadget'), str(work / 'check.c'),
                    '-o', str(work / 'check')], check=True)
    subprocess.run([str(work / 'check')], check=True)
