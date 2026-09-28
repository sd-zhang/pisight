/* Test-only I2S replacement: deterministic S32 stereo source, mmap access.
 * ALSA's file/null mmap capture skips file input on partial commits, so use
 * this PCM to preserve samples across arbitrary read sizes and prepare calls.
 */
#define _POSIX_C_SOURCE 200809L
#include <alsa/asoundlib.h>
#include <alsa/pcm_external.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct fixture { snd_pcm_ioplug_t io; FILE *input; };
static int start(snd_pcm_ioplug_t *io) { (void)io; return 0; }
static int stop(snd_pcm_ioplug_t *io) { (void)io; return 0; }
static snd_pcm_sframes_t pointer(snd_pcm_ioplug_t *io)
{ return (snd_pcm_sframes_t)((io->appl_ptr + io->period_size) % io->buffer_size); }
static int prepare(snd_pcm_ioplug_t *io)
{ struct fixture *f = io->private_data; rewind(f->input); return 0; }
static int close_pcm(snd_pcm_ioplug_t *io)
{ struct fixture *f = io->private_data; fclose(f->input); free(f); return 0; }
static snd_pcm_sframes_t transfer(snd_pcm_ioplug_t *io,
	const snd_pcm_channel_area_t *areas, snd_pcm_uframes_t offset,
	snd_pcm_uframes_t frames)
{
	struct fixture *f = io->private_data;
	/* mmap_begin may request more than mmap_commit consumes. Reconstruct from
	 * committed appl_ptr, never advance the source just because begin ran. */
	if (fseek(f->input, (long)(io->appl_ptr*8), SEEK_SET)) return -EIO;
	for (snd_pcm_uframes_t i = 0; i < frames; ++i) {
		unsigned char pair[8] = {0};
		(void)fread(pair, 1, 8, f->input);
		for (unsigned ch = 0; ch < 2; ++ch) {
			unsigned char *out = (unsigned char *)areas[ch].addr +
				areas[ch].first/8 + (offset+i)*areas[ch].step/8;
			memcpy(out, pair+ch*4, 4);
		}
	}
	return (snd_pcm_sframes_t)frames;
}
static const snd_pcm_ioplug_callback_t callbacks = {
	.start=start, .stop=stop, .pointer=pointer, .transfer=transfer,
	.prepare=prepare, .close=close_pcm,
};
SND_PCM_PLUGIN_DEFINE_FUNC(fixture)
{
	(void)root; (void)conf;
	if (stream != SND_PCM_STREAM_CAPTURE) return -EINVAL;
	struct fixture *f = calloc(1, sizeof *f);
	if (!f) return -ENOMEM;
	f->input = fopen("/work/bandpass/input.s32", "rb");
	if (!f->input) { free(f); return -ENOENT; }
	f->io.version = SND_PCM_IOPLUG_VERSION;
	f->io.name = "Synthetic I2S fixture";
	f->io.callback = &callbacks;
	f->io.private_data = f;
	f->io.mmap_rw = 1;
	int e = snd_pcm_ioplug_create(&f->io, name, stream, mode);
	if (e < 0) { fclose(f->input); free(f); return e; }
	unsigned access = SND_PCM_ACCESS_MMAP_INTERLEAVED, format = SND_PCM_FORMAT_S32_LE;
	if ((e=snd_pcm_ioplug_set_param_list(&f->io,SND_PCM_IOPLUG_HW_ACCESS,1,&access))<0 ||
	    (e=snd_pcm_ioplug_set_param_list(&f->io,SND_PCM_IOPLUG_HW_FORMAT,1,&format))<0 ||
	    (e=snd_pcm_ioplug_set_param_minmax(&f->io,SND_PCM_IOPLUG_HW_CHANNELS,2,2))<0 ||
	    (e=snd_pcm_ioplug_set_param_minmax(&f->io,SND_PCM_IOPLUG_HW_RATE,8000,96000))<0 ||
	    (e=snd_pcm_ioplug_set_param_minmax(&f->io,SND_PCM_IOPLUG_HW_PERIOD_BYTES,128,32768))<0 ||
	    (e=snd_pcm_ioplug_set_param_minmax(&f->io,SND_PCM_IOPLUG_HW_BUFFER_BYTES,256,65536))<0 ||
	    (e=snd_pcm_ioplug_set_param_minmax(&f->io,SND_PCM_IOPLUG_HW_PERIODS,2,8))<0) {
		snd_pcm_ioplug_delete(&f->io); return e;
	}
	*pcmp=f->io.pcm;
	return 0;
}
SND_PCM_PLUGIN_SYMBOL(fixture);
