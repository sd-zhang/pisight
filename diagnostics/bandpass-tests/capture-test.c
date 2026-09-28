/* Exercise the installed ALSA PCM plugin, route, format negotiation and
 * repeated capture with file-backed hardware. No real device is opened. */
#define _POSIX_C_SOURCE 200809L
#include <alsa/asoundlib.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	if (argc != 7) return 2;
	snd_pcm_t *pcm;
	int err = snd_pcm_open(&pcm, "pisight_mic", SND_PCM_STREAM_CAPTURE, 0);
	if (err < 0) { fprintf(stderr, "open: %s\n", snd_strerror(err)); return 3; }
	err = snd_pcm_set_params(pcm, SND_PCM_FORMAT_S16_LE,
		SND_PCM_ACCESS_RW_INTERLEAVED, (unsigned)atoi(argv[5]),
		(unsigned)atoi(argv[4]), 0, 50000);
	if (err < 0) {
		fprintf(stderr, "params: %s\n", snd_strerror(err));
		snd_pcm_close(pcm);
		return atoi(argv[6]) ? 0 : 4;
	}
	if (atoi(argv[6])) { snd_pcm_close(pcm); return 5; }
	FILE *out = fopen(argv[1], "wb");
	if (!out) return 6;
	int remaining = atoi(argv[2]), chunk = atoi(argv[3]);
	int16_t buf[4096];
	if (chunk < 1 || chunk > 4096) return 7;
	if (getenv("TEST_RESTART")) {
		/* The fixture rewinds on prepare. Same handle must reproduce startup. */
		if (snd_pcm_readi(pcm, buf, 1024) != 1024 ||
		    snd_pcm_drop(pcm) < 0 || snd_pcm_prepare(pcm) < 0) return 10;
	}
	while (remaining > 0) {
		int n = remaining < chunk ? remaining : chunk;
		snd_pcm_sframes_t got = snd_pcm_readi(pcm, buf, (snd_pcm_uframes_t)n);
		if (got <= 0) { fprintf(stderr, "read: %ld\n", (long)got); return 8; }
		if (fwrite(buf, 2, (size_t)got, out) != (size_t)got) return 9;
		remaining -= (int)got;
	}
	fclose(out);
	snd_pcm_close(pcm);
	return 0;
}
