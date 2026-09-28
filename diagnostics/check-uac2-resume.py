#!/usr/bin/env python3
"""Exercise the pinned UAC2 suspend/resume callbacks with stub hardware state."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    '/private/tmp/pisight-stream-source/linux-custom/drivers/usb/gadget/function')


def function(source, name):
    match = re.search(r'\b' + name + r'\s*\([^;]*?\)\s*\{', source, re.S)
    if not match:
        raise AssertionError(f'missing {name}')
    depth = 1
    end = match.end()
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]


audio = (SOURCE / 'u_audio.c').read_text()
uac2 = (SOURCE / 'f_uac2.c').read_text()
header = (SOURCE / 'u_audio.h').read_text()
assert 'void u_audio_resume(struct g_audio *g_audio);' in header
assert 'uac2->g_audio.func.resume = afunc_resume;' in uac2

harness = r'''
#include <stdbool.h>
#include <stdio.h>
struct uac_rtd_params { bool active, ep_enabled; int lock, snd_kctl_rate_id; struct snd_uac_chip *uac; };
struct snd_uac_chip { struct uac_rtd_params p_prm, c_prm; void *card; };
struct g_audio { struct snd_uac_chip *uac; };
struct usb_function { int dummy; };
struct f_uac2 { struct g_audio g_audio; };
static struct f_uac2 instance;
static int notifications, endpoint_starts;
#define SNDRV_CTL_EVENT_MASK_VALUE 1
#define spin_lock_irqsave(lock, flags) ((void)(lock), (void)(flags))
#define spin_unlock_irqrestore(lock, flags) ((void)(lock), (void)(flags))
#define snd_ctl_notify(card, mask, id) ((void)(card), (void)(mask), (void)(id), ++notifications)
#define EXPORT_SYMBOL_GPL(name)
#define func_to_uac2(fn) ((void)(fn), &instance)
'''
harness += '\n'.join(prefix + function(source, name) for source, name, prefix in (
    (audio, 'set_active', 'static void '),
    (audio, 'u_audio_suspend', 'void '),
    (audio, 'u_audio_resume', 'void '),
    (uac2, 'afunc_suspend', 'static void '),
    (uac2, 'afunc_resume', 'static void ')))
harness += r'''
int main(void) {
    struct snd_uac_chip chip = {0};
    struct usb_function fn = {0};
    instance.g_audio.uac = &chip;
    chip.p_prm.uac = &chip;
    chip.c_prm.uac = &chip;

    /* Fresh alt 0: neither endpoint is active or restarted. */
    afunc_suspend(&fn); afunc_resume(&fn);
    if (chip.p_prm.active || chip.c_prm.active || notifications || endpoint_starts) return 1;

    /* IN alt 1 survives suspend; only its activity notification returns. */
    chip.p_prm.ep_enabled = true;
    chip.p_prm.active = true;
    afunc_suspend(&fn);
    if (chip.p_prm.active || notifications != 1) return 2;
    afunc_resume(&fn);
    if (!chip.p_prm.active || chip.c_prm.active || notifications != 2 || endpoint_starts) return 3;
    afunc_resume(&fn);
    if (notifications != 2 || endpoint_starts) return 4;

    /* OUT alt 1 independently follows its endpoint state. */
    chip.c_prm.ep_enabled = true;
    chip.c_prm.active = true;
    afunc_suspend(&fn);
    if (chip.p_prm.active || chip.c_prm.active || notifications != 4) return 5;
    chip.p_prm.ep_enabled = false;
    afunc_resume(&fn);
    if (chip.p_prm.active || !chip.c_prm.active || notifications != 5 || endpoint_starts) return 6;
    puts("PASS: inactive, active, duplicate resume and independent endpoints");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='pisight-uac2-resume-') as directory:
    path = Path(directory)
    (path / 'test.c').write_text(harness)
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                    str(path / 'test.c'), '-o', str(path / 'test')], check=True)
    subprocess.run([str(path / 'test')], check=True)
