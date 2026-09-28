/* Production shutter.c with only GPIO/sysfs/event-loop boundaries replaced. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include "gpio-uapi.h"
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "events.h"
#include "stream.h"

_Static_assert(sizeof(struct gpio_v2_line_request) == 592, "GPIO v2 request ABI");
_Static_assert(offsetof(struct gpio_v2_line_request, fd) == 588, "GPIO v2 fd ABI");
_Static_assert(sizeof(struct gpio_v2_line_config) == 272, "GPIO v2 config ABI");
_Static_assert(sizeof(struct gpio_v2_line_values) == 16, "GPIO v2 values ABI");
_Static_assert(sizeof(struct gpio_v2_line_event) == 48, "GPIO v2 event ABI");
_Static_assert(GPIO_V2_GET_LINE_IOCTL == 0xc250b407UL, "GPIO v2 request ioctl");
_Static_assert(GPIO_V2_LINE_GET_VALUES_IOCTL == 0xc010b40eUL, "GPIO v2 value ioctl");

static int level, writes, reads, gets, stopped, blocked, event_ready;
static int fail_values, fail_write, fail_request, requested, released;
static char commands[16][16];
static void (*event_cb)(void *);
static void *event_data;
static int fake_open(const char *name, int flags, ...) {
    (void)flags;
    if (!strcmp(name, "/dev/gpiochip0")) return 10;
    assert(!strcmp(name, "/sys/class/udc/20980000.usb/soft_connect"));
    return 12;
}
static int fake_close(int fd) {
    if (fd == 11) released++;
    return 0;
}
static int fake_ioctl(int fd, unsigned long request, ...) {
    va_list args; va_start(args, request); void *arg = va_arg(args, void *); va_end(args);
    if (request == GPIO_GET_CHIPINFO_IOCTL) {
        assert(fd == 10);
        struct gpiochip_info *info = arg;
        strcpy(info->label, "pinctrl-bcm2835"); info->lines = 54; return 0;
    }
    if (request == GPIO_V2_GET_LINE_IOCTL) {
        struct gpio_v2_line_request *r = arg;
        assert(fd == 10 && r->num_lines == 1 && r->offsets[0] == 26);
        assert(r->config.flags & GPIO_V2_LINE_FLAG_INPUT);
        assert(r->config.flags & GPIO_V2_LINE_FLAG_EDGE_RISING);
        assert(r->config.flags & GPIO_V2_LINE_FLAG_EDGE_FALLING);
        assert(r->config.num_attrs == 1);
        assert(r->config.attrs[0].attr.id == GPIO_V2_LINE_ATTR_ID_DEBOUNCE);
        assert(r->config.attrs[0].attr.debounce_period_us >= 20000);
        if (fail_request) { errno = EBUSY; return -1; }
        r->fd = 11; requested++; return 0;
    }
    assert(fd == 11 && request == GPIO_V2_LINE_GET_VALUES_IOCTL);
    gets++;
    if (fail_values) { errno = EIO; return -1; }
    struct gpio_v2_line_values *v = arg;
    assert(v->mask == 1); v->bits = level; return 0;
}
static ssize_t fake_read(int fd, void *buf, size_t size) {
    assert(fd == 11); reads++;
    if (!event_ready) { errno = EAGAIN; return -1; }
    assert(size >= sizeof(struct gpio_v2_line_event));
    struct gpio_v2_line_event event = { .id = level ? GPIO_V2_LINE_EVENT_RISING_EDGE : GPIO_V2_LINE_EVENT_FALLING_EDGE };
    memcpy(buf, &event, sizeof(event)); event_ready = 0; return sizeof(event);
}
static ssize_t fake_write(int fd, const void *buf, size_t size) {
    assert(fd == 12 && writes < 16 && size < 16);
    if (fail_write) { errno = EIO; return -1; }
    memcpy(commands[writes], buf, size); commands[writes++][size] = 0; return size;
}
void events_watch_fd(struct events *e, int fd, enum event_type type, void (*cb)(void *), void *data) {
    assert(fd == 11 && type == EVENT_READ); FD_SET(fd, &e->rfds); event_cb = cb; event_data = data;
}
void events_unwatch_fd(struct events *e, int fd, enum event_type type) {
    assert(fd == 11 && type == EVENT_READ); FD_CLR(fd, &e->rfds); event_cb = NULL;
}
void events_stop(struct events *e) { (void)e; stopped++; }
void uvc_stream_set_shutter_closed(struct uvc_stream *s, int closed) { (void)s; blocked = closed; }

#define open fake_open
#define close fake_close
#define ioctl fake_ioctl
#define read fake_read
#define write fake_write
#include "shutter.c"
#undef open
#undef close
#undef ioctl
#undef read
#undef write

static void edge(int value) { level = value; event_ready = 1; event_cb(event_data); }
static void reset(void) {
    level = writes = reads = gets = stopped = blocked = event_ready = 0;
    fail_values = fail_write = fail_request = requested = released = 0;
    memset(commands, 0, sizeof(commands)); event_cb = NULL;
}
int main(void) {
    struct events events = {0};
    for (int initial = 0; initial <= 1; initial++) {
        reset(); level = initial;
        struct shutter *s = shutter_create(&events, "20980000.usb");
        assert(s && requested == 1 && writes == 1);
        assert(!strcmp(commands[0], "disconnect")); // No enumeration before initialization.
        assert(!shutter_start(s, (struct uvc_stream *)1));
        assert(blocked == initial);
        assert(!strcmp(commands[writes-1], initial ? "disconnect" : "connect"));
        int oldwrites = writes;
        edge(initial); assert(writes == oldwrites); // Duplicate state causes no USB churn.
        edge(!initial); assert(blocked == !initial && writes == oldwrites + 1);
        assert(!strcmp(commands[writes-1], initial ? "connect" : "disconnect"));
        edge(initial); assert(blocked == initial && writes == oldwrites + 2);
        fail_values = 1; edge(!initial);
        assert(stopped == 1 && blocked == 1);
        assert(!strcmp(commands[writes-1], "disconnect")); // Read failure cannot reopen.
        shutter_destroy(s); assert(released == 1 && !event_cb);
    }
    reset(); fail_request = 1;
    assert(!shutter_create(&events, "20980000.usb"));
    assert(requested == 0 && released == 0);
    reset(); struct shutter *s = shutter_create(&events, "20980000.usb");
    assert(s); fail_write = 1;
    assert(shutter_start(s, (struct uvc_stream *)1) < 0 && blocked == 1);
    shutter_destroy(s); assert(released == 1);
    puts("PASS: boot open/closed, transitions, duplicates, GPIO failure and USB failure");
}
