/* Tests real DSP; --baseline represents the existing unfiltered mono path.
 * Wrong cutoff/sign/order, quantization, or retained state should fail these. */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifndef BASELINE
#include "voice-filter.h"
#else
struct voice_filter { int unused; };
static void voice_filter_reset(struct voice_filter *f) { (void)f; }
static int16_t voice_filter_sample(struct voice_filter *f, int16_t x)
{ (void)f; return x; }
#endif
static const double pi = 3.14159265358979323846;
static int failures;
static void check(int ok, const char *name)
{
	printf("%s: %s\n", ok ? "PASS" : "FAIL", name);
	if (!ok) ++failures;
}
static double response(double hz)
{
	struct voice_filter f;
	voice_filter_reset(&f);
	double in = 0, out = 0;
	for (int i = 0; i < 96000; ++i) {
		int16_t x = (int16_t)lround(12000 * sin(2*pi*hz*i/48000));
		int16_t y = voice_filter_sample(&f, x);
		if (i >= 48000) { in += (double)x*x; out += (double)y*y; }
	}
	return 10*log10(out/in);
}
int main(int argc, char **argv)
{
	struct voice_filter f;
	voice_filter_reset(&f);
	if (argc == 2 && !strcmp(argv[1], "--raw")) {
		int16_t x;
		while (fread(&x, sizeof x, 1, stdin) == 1) {
			int16_t y = voice_filter_sample(&f, x);
			if (fwrite(&y, sizeof y, 1, stdout) != 1) return 2;
		}
		return ferror(stdin) || ferror(stdout);
	}
	if (argc == 2 && !strcmp(argv[1], "--bench")) {
		volatile int64_t checksum = 0;
		clock_t start = clock();
		for (int i = 0; i < 4800000; ++i)
			checksum += voice_filter_sample(&f, (int16_t)(i*17U));
		double seconds = (double)(clock()-start)/CLOCKS_PER_SEC;
		printf("100 audio seconds: %.6f CPU seconds, %.4f%% of real time, checksum=%lld\n",
		       seconds, seconds, (long long)checksum);
		return 0;
	}
	/* Independent bilinear Butterworth magnitude: no DSP coefficient reuse. */
	double frequencies[] = {20, 40, 80, 160, 1000, 4000, 8000, 12000, 16000, 20000};
	for (unsigned i = 0; i < sizeof frequencies/sizeof *frequencies; ++i) {
		double hz = frequencies[i], w = tan(pi*hz/48000);
		double hp = pow(tan(pi*80/48000)/w, 4);
		double lp = pow(w/tan(pi*8000/48000), 4);
		double expected = -10*log10((1+hp)*(1+lp));
		double actual = response(hz);
		printf("%.0f Hz: measured %.4f dB, expected %.4f dB\n", hz, actual, expected);
		check(fabs(actual-expected) < 0.12, "frequency response within 0.12 dB");
	}
	voice_filter_reset(&f);
	int max_dc = 0;
	for (int i = 0; i < 96000; ++i) {
		int y = voice_filter_sample(&f, 20000);
		if (i > 48000 && abs(y) > max_dc) max_dc = abs(y);
	}
	check(max_dc <= 2, "constant DC settles within two PCM counts");
	voice_filter_reset(&f);
	int silence = 0;
	for (int i = 0; i < 48000; ++i) silence |= voice_filter_sample(&f, 0);
	check(silence == 0, "reset starts silent with no prior-session history");
	/* Reset must reproduce an impulse after a loud previous session. */
	int16_t impulse[2048];
	for (int i = 0; i < 2048; ++i) impulse[i] = voice_filter_sample(&f, i ? 0 : 32767);
	for (int i = 0; i < 48000; ++i) (void)voice_filter_sample(&f, -32768);
	voice_filter_reset(&f);
	int same = 1;
	for (int i = 0; i < 2048; ++i)
		if (voice_filter_sample(&f, i ? 0 : 32767) != impulse[i]) same = 0;
	check(same, "new session reproduces impulse after previous stream");
	/* Extreme steps have transient overshoot: output must saturate, not wrap. */
	voice_filter_reset(&f);
	for (int i = 0; i < 48000; ++i) (void)voice_filter_sample(&f, -32768);
	int peak = 0, first_negative = 0;
	for (int i = 0; i < 30; ++i) {
		int y = voice_filter_sample(&f, 32767);
		if (y < 0) first_negative = 1;
		if (y > peak) peak = y;
	}
	check(!first_negative && peak == 32767, "positive overload clips without polarity wrap");
	for (int i = 0; i < 96000; ++i) (void)voice_filter_sample(&f, 0);
	int tail = 0;
	for (int i = 0; i < 48000; ++i) tail |= voice_filter_sample(&f, 0);
	check(tail == 0, "silence after excitation decays to zero");
	printf("%d failures\n", failures);
	return failures != 0;
}
