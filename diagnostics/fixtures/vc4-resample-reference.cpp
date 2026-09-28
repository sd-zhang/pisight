/* SPDX-License-Identifier: BSD-2-Clause
 * Copyright (C) 2019-2021, Raspberry Pi Ltd
 * Reference from libcamera v0.5.0 src/ipa/rpi/vc4/vc4.cpp.
 */
void reference(uint16_t dest[], const std::vector<double> &src,
			   int destW, int destH)
{
	/*
	 * Precalculate and cache the x sampling locations and phases to
	 * save recomputing them on every row.
	 */
	assert(destW > 1 && destH > 1 && destW <= 64);
	int xLo[64], xHi[64];
	double xf[64];
	double x = -0.5, xInc = 16.0 / (destW - 1);
	for (int i = 0; i < destW; i++, x += xInc) {
		xLo[i] = floor(x);
		xf[i] = x - xLo[i];
		xHi[i] = xLo[i] < 15 ? xLo[i] + 1 : 15;
		xLo[i] = xLo[i] > 0 ? xLo[i] : 0;
	}

	/* Now march over the output table generating the new values. */
	double y = -0.5, yInc = 12.0 / (destH - 1);
	for (int j = 0; j < destH; j++, y += yInc) {
		int yLo = floor(y);
		double yf = y - yLo;
		int yHi = yLo < 11 ? yLo + 1 : 11;
		yLo = yLo > 0 ? yLo : 0;
		double const *rowAbove = src.data() + yLo * 16;
		double const *rowBelow = src.data() + yHi * 16;
		for (int i = 0; i < destW; i++) {
			double above = rowAbove[xLo[i]] * (1 - xf[i]) + rowAbove[xHi[i]] * xf[i];
			double below = rowBelow[xLo[i]] * (1 - xf[i]) + rowBelow[xHi[i]] * xf[i];
			int result = floor(1024 * (above * (1 - yf) + below * yf) + .5);
			*(dest++) = result > 16383 ? 16383 : result; /* want u4.10 */
		}
	}
}
