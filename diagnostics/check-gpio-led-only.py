#!/usr/bin/env python3
"""Run real gpio.c against a write-only GPIO boundary; input monitoring is unavailable."""
import pathlib
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='pisight-gpio-check-') as directory:
    work = pathlib.Path(directory)
    (work / 'pigpiod_if2.h').write_text('''
#include <stdint.h>
#define PI_OUTPUT 1
#define PI_INPUT 0
#define PI_BAD_GPIO -2
#define PI_BAD_MODE -4
#define PI_BAD_LEVEL -5
#define PI_NOT_PERMITTED -41
#define PI_BAD_FILTER -125
#define EITHER_EDGE 2
int pigpio_start(char *, char *);
void pigpio_stop(int);
int gpio_write(int, unsigned, unsigned);
int set_mode(int, unsigned, unsigned);
int set_glitch_filter(int, unsigned, unsigned);
int gpio_read(int, unsigned);
int callback_ex(int, unsigned, unsigned, void (*)(int,uint32_t,uint32_t,uint32_t,void *), void *);
''')
    (work / 'check.c').write_text('''
#include <stdio.h>
#include <string.h>
#include "pigpiod_if2.h"
#include "gpio.h"
static int levels[2], modes[2], input_calls, stopped;
static int slot(unsigned pin) { return pin == 23 ? 0 : pin == 24 ? 1 : -1; }
int pigpio_start(char *host, char *port) { (void)host; (void)port; return 7; }
void pigpio_stop(int pi) { if (pi == 7) stopped++; }
int gpio_write(int pi, unsigned pin, unsigned level) {
    int index = slot(pin);
    if (pi != 7 || index < 0 || level > 1) { input_calls++; return -2; }
    levels[index] = level; return 0;
}
int set_mode(int pi, unsigned pin, unsigned mode) {
    int index = slot(pin);
    if (pi != 7 || index < 0) { input_calls++; return -2; }
    modes[index] = mode; return 0;
}
int set_glitch_filter(int pi, unsigned pin, unsigned delay) {
    (void)pi; (void)pin; (void)delay; input_calls++; return -125;
}
int gpio_read(int pi, unsigned pin) { (void)pi; (void)pin; input_calls++; return -2; }
int callback_ex(int pi, unsigned pin, unsigned edge,
    void (*cb)(int,uint32_t,uint32_t,uint32_t,void *), void *data) {
    (void)pi; (void)pin; (void)edge; (void)cb; (void)data; input_calls++; return -2;
}
int main(int argc, char **argv) {
    (void)argc;
    struct gpio_ctrl *gpio = gpio_create(argv[1]);
    if (!gpio) { puts("FAIL: LED pin configuration rejected"); return 1; }
    if (gpio_init(gpio)) { puts("FAIL: LED startup requires shutter input/alerts"); return 1; }
    if (input_calls || levels[0] != LOW || levels[1] != LOW || modes[0] != PI_OUTPUT || modes[1] != PI_OUTPUT)
        return 2;
    if (gpio_set_pin_state(gpio, STREAMING, HIGH) || levels[1] != HIGH) return 3;
    if (gpio_set_pin_state(gpio, STREAMING, LOW) || levels[1] != LOW) return 4;
    gpio_cleanup(gpio);
    if (levels[0] || levels[1] || modes[0] || modes[1] || input_calls || stopped != 1)
        return 5;
    puts("PASS: LEDs initialize, toggle and clean up without any shutter I/O");
    return 0;
}
''')
    binary = work / 'check'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(work), '-I' + str(source / 'include/uvcgadget'),
                    str(source / 'lib/gpio.c'), str(work / 'check.c'), '-o', str(binary)], check=True)
    failed = 0
    for pins in ['23 24', '23 24 26']:
        print('Pins:', pins, flush=True)
        failed += subprocess.run([str(binary), pins]).returncode != 0
    sys.exit(bool(failed))
