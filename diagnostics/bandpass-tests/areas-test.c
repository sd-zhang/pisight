/* Real transfer callback with nonzero offsets, padded/unaligned channel areas.
 * Catches stride/offset errors and loss of S32 fractional precision. */
#include "pcm_pisight_voice.c"
#include <assert.h>
#include <stdio.h>

int main(void)
{
	struct voice_pcm v = {0};
	v.ext.private_data = &v;
	v.ext.rate = 48000;
	assert(voice_init(&v.ext) == 0);
	unsigned char input[6000] = {0}, output[6000];
	memset(output, 0xa5, sizeof output);
	snd_pcm_channel_area_t src = {input, 8, 64}, dst = {output, 24, 48};
	struct voice_filter reference;
	voice_filter_reset(&reference);
	int16_t expected[500];
	for (int i = 0; i < 500; ++i) {
		int32_t x = (i%4 == 0 ? INT32_MIN : i%4 == 1 ? INT32_MAX : i*17539);
		uint32_t bits = (uint32_t)x;
		for (int b = 0; b < 4; ++b) input[1+(i+3)*8+b] = bits >> (8*b);
		expected[i] = voice_filter_sample(&reference, x / 65536.0f);
	}
	assert(voice_transfer(&v.ext, &dst, 5, &src, 3, 137) == 137);
	assert(voice_transfer(&v.ext, &dst, 142, &src, 140, 363) == 363);
	for (int i = 0; i < 500; ++i) {
		unsigned off = 3+(i+5)*6;
		assert(output[off] == ((uint16_t)expected[i] & 255));
		assert(output[off+1] == ((uint16_t)expected[i] >> 8));
	}
	for (unsigned i = 0; i < sizeof output; ++i) {
		int in_sample = i >= 33 && i < 3033 && (i-33)%6 < 2;
		if (!in_sample) assert(output[i] == 0xa5);
	}
	assert(voice_init(&v.ext) == 0);
	assert(v.filter.hp1 == 0 && v.filter.lp1 == 0);
	v.ext.rate = 44100;
	assert(voice_init(&v.ext) == -EINVAL);
	src.first = 1;
	assert(voice_transfer(&v.ext, &dst, 0, &src, 0, 1) == -EINVAL);
	/* Cover up to 8192 frames (larger than the 50 ms bridge buffer). */
	for (int block = 1; block <= 8192; block *= 2) {
		voice_filter_reset(&v.filter);
		(void)voice_filter_sample(&v.filter, 32767);
		for (int n = 0; n < 480000; n += block) {
			for (int j = 0; j < block; ++j) (void)voice_filter_sample(&v.filter, 0);
			voice_filter_quiet_tail(&v.filter);
		}
		assert(v.filter.hp1 == 0 && v.filter.hp2 == 0 &&
		       v.filter.lp1 == 0 && v.filter.lp2 == 0);
	}
	puts("PASS: real transfer offsets, strides, LE samples, split blocks, bounds, reset and rate guard");
	return 0;
}
