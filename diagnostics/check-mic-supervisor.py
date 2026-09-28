#!/usr/bin/env python3
"""Run the real supervisor with fake ALSA events and real child processes.

No USB/audio hardware is accessed. Verifies startup, toggles, retries and cleanup;
does not establish audio timing or Pi USB performance.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'webcampi/package/pisight-mic/pisight-mic.c'

HEADER = r'''
#include <stdlib.h>
#include <unistd.h>
#include <poll.h>
#include <errno.h>
#include <time.h>
typedef int snd_ctl_t;
typedef struct { long value; } snd_ctl_elem_value_t;
typedef struct { int type, mask, iface; const char *name; } snd_ctl_event_t;
#define SND_CTL_NONBLOCK 1
#define SND_CTL_ELEM_IFACE_PCM 3
#define SND_CTL_EVENT_ELEM 1
#define SND_CTL_EVENT_MASK_VALUE 1
#define snd_ctl_elem_value_alloca(p) snd_ctl_elem_value_t v = {0}; *(p) = &v
#define snd_ctl_event_alloca(p) snd_ctl_event_t ev = {0}; *(p) = &ev
static long rate;
static int pending_fds[2] = {-1,-1};
static int snd_ctl_open(snd_ctl_t **p, const char *n, int f) {
 (void)n; (void)f; static int ctl; *p=&ctl;
 rate=atol(getenv("INITIAL_RATE")); return 0;
}
static int snd_ctl_close(snd_ctl_t *p) {(void)p; return 0;}
static int snd_ctl_subscribe_events(snd_ctl_t *p,int n) {
 (void)p;(void)n;
 if(getenv("PAUSE_AFTER_SUBSCRIBE")) {
  if(pipe(pending_fds)) return -EIO;
  if(write(pending_fds[1],"1",1)!=1) return -EIO;
 }
 return 0;
}
static void snd_ctl_elem_value_set_interface(snd_ctl_elem_value_t*p,int n){(void)p;(void)n;}
static void snd_ctl_elem_value_set_name(snd_ctl_elem_value_t*p,const char*n){(void)p;(void)n;}
static int snd_ctl_elem_read(snd_ctl_t*p,snd_ctl_elem_value_t*v){(void)p;v->value=rate;return 0;}
static long snd_ctl_elem_value_get_integer(snd_ctl_elem_value_t*v,int n){(void)n;return v->value;}
static int snd_ctl_poll_descriptors_count(snd_ctl_t*p){(void)p;return 1;}
static int snd_ctl_poll_descriptors(snd_ctl_t*p,struct pollfd*f,unsigned n){
 (void)p;(void)n;f->fd=pending_fds[0]>=0?pending_fds[0]:0;f->events=POLLIN;return 1;
}
static int snd_ctl_read(snd_ctl_t*p,snd_ctl_event_t*e){
 (void)p;int fd=pending_fds[0]>=0?pending_fds[0]:0;
 struct pollfd f={fd,POLLIN,0}; char b;
 if(poll(&f,1,0)<=0)return -EAGAIN;
 if(read(fd,&b,1)!=1)return -EIO;
 e->type=SND_CTL_EVENT_ELEM;e->mask=SND_CTL_EVENT_MASK_VALUE;
 e->iface=SND_CTL_ELEM_IFACE_PCM;e->name="Playback Rate";
 if(b=='x')e->name="Playback Volume";
 else if(b=='m')e->mask=2;
 else rate=b=='1'?48000:b=='2'?44100:0;
 return 1;
}
#define snd_ctl_event_get_type(e) ((e)->type)
#define snd_ctl_event_elem_get_mask(e) ((e)->mask)
#define snd_ctl_event_elem_get_interface(e) ((e)->iface)
#define snd_ctl_event_elem_get_name(e) ((e)->name)
static const char *snd_strerror(int n){(void)n;return "fake ALSA error";}
'''

with tempfile.TemporaryDirectory(prefix='pisight-mic-test-') as tmp:
    tmp = Path(tmp)
    (tmp / 'alsa').mkdir()
    (tmp / 'alsa/asoundlib.h').write_text(HEADER)
    proc = tmp / 'proc'
    pcm = proc / 'asound/card1/pcm0p/sub0'
    pcm.mkdir(parents=True)
    (pcm / 'status').write_text('state: RUNNING\ndelay: 2400\n')
    (pcm / 'hw_params').write_text('rate: 48000 (48000/1)\n')
    diag = tmp / 'diagnostics-enabled'
    diag.write_text('1\n')
    child = tmp / 'alsaloop'
    child.write_text('''#!/usr/bin/env python3
import os,signal,time
with open(os.environ['CHILD_LOG'],'a') as f: f.write(str(os.getpid())+'\\n')
if os.environ.get('CRASH'): raise SystemExit(1)
if os.environ.get('IGNORE_TERM'): signal.signal(signal.SIGTERM,signal.SIG_IGN)
while True: time.sleep(1)
''')
    child.chmod(0o755)
    binary = tmp / 'supervisor'
    subprocess.run(['cc', '-std=c99', '-D_POSIX_C_SOURCE=200809L', '-Wall',
                    '-Wextra', '-Werror', '-I', str(tmp),
                    f'-DALSALOOP_PATH="{child}"', f'-DPROC_ROOT="{proc}"', f'-DDIAGNOSTICS_RUNTIME_PATH="{diag}"',
                    str(SOURCE), '-o', str(binary)], check=True)

    def wait_for(test, timeout=3):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if test(): return
            time.sleep(.025)
        raise AssertionError('condition timed out')

    def alive(pid):
        try: os.kill(pid, 0); return True
        except ProcessLookupError: return False

    for name, initial, extra in [
        ('idle and toggles', '0', {}),
        ('diagnostics off', '48000', {'DIAG_OFF': '1'}),
        ('already active at boot', '48000', {}),
        ('queued event at boot', '48000', {'PAUSE_AFTER_SUBSCRIBE': '1'}),
        ('bounded crash retry', '48000', {'CRASH': '1'}),
        ('unresponsive child cleanup', '48000', {'IGNORE_TERM': '1'}),
    ]:
        diag.write_text('0\n' if extra.get('DIAG_OFF') else '1\n')
        log = tmp / (name + '.pids')
        env = dict(os.environ, INITIAL_RATE=initial, CHILD_LOG=str(log), **extra)
        p = subprocess.Popen([str(binary)], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
        def pids(): return [int(x) for x in log.read_text().split()] if log.exists() else []
        def change(value): p.stdin.write(value); p.stdin.flush()
        try:
            if initial == '0':
                time.sleep(.4)
                assert not pids(), 'bridge must remain stopped while host is inactive'
                change(b'1')
            wait_for(lambda: len(pids()) == 1)
            if extra.get('CRASH'):
                wait_for(lambda: len(pids()) >= 2)
                time.sleep(.3)
                assert len(pids()) == 2, 'failed child respawned without backoff'
            elif extra.get('PAUSE_AFTER_SUBSCRIBE'):
                time.sleep(1.5)
                assert len(pids()) == 1, 'queued initial event restarted bridge'
            elif not extra:
                first = pids()[0]
                change(b'x')
                time.sleep(.3)
                assert len(pids()) == 1, 'unrelated control event restarted bridge'
                change(b'm')
                time.sleep(.3)
                assert len(pids()) == 1, 'non-value rate event restarted bridge'
                change(b'1')
                wait_for(lambda: len(pids()) == 2)
                assert not alive(first), 'new active notification retained old bridge'
                first = pids()[-1]
                change(b'01')
                wait_for(lambda: len(pids()) == 3)
                assert not alive(first), 'coalesced close/open retained old bridge'
                first = pids()[-1]
                change(b'0')
                wait_for(lambda: not alive(first))
                change(b'2')
                time.sleep(.3)
                assert len(pids()) == 3, 'unsupported sample rate started bridge'
                change(b'1')
                wait_for(lambda: len(pids()) == 4)
            p.terminate()
            p.wait(timeout=3)
            stderr = p.stderr.read().decode()
            assert p.returncode == 0, stderr
            if extra.get('PAUSE_AFTER_SUBSCRIBE'):
                assert stderr.count('microphone bridge started') == 1, stderr
                assert 'microphone diagnostic uptime=' in stderr, stderr
                assert 'trigger=periodic' in stderr, stderr
                assert 'trigger=pre-stop' in stderr, stderr
                assert 'state: RUNNING\ndelay: 2400' in stderr, stderr
                assert 'rate: 48000 (48000/1)' in stderr, stderr
            if extra.get('DIAG_OFF'): assert 'microphone diagnostic uptime=' not in stderr
            assert not any(alive(pid) for pid in pids()), 'orphan bridge after supervisor exit'
            print('PASS:', name)
        finally:
            if p.poll() is None: p.kill(); p.wait()
            for pid in pids():
                if alive(pid): os.kill(pid, 9)
