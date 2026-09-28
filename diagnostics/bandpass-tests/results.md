# Fixed voice band-pass — 2026-09-28

User narrowed the request to a fixed band-pass, no adjustment, then testing.
Implemented 80 Hz high-pass followed by 8 kHz low-pass, both second-order
Butterworth (12 dB/octave), at 48 kHz. No parametric EQ, gain controls, UVC
settings, persistence, web UI, serial interface or extra service was added.

## Audio path

Existing left-slot ALSA route -> mono S32 -> two float biquads -> saturating,
rounded S16 -> existing alsaloop -> existing USB microphone. The filter runs
inside ALSA transfers, allocating no memory and adding no queue or lookahead.
Filter phase delay remains; acoustic end-to-end latency has not been measured.
The mic supervisor, host-open gating, 50 ms bridge target and USB timing are
unchanged. Filter state resets on ALSA prepare/reset, including new sessions.
Output can saturate on extreme transients; this is clipping protection, not a
limiter, gain boost or noise suppression. Silence cleanup clears section state
pairs together below 1e-15 PCM units to avoid expensive denormal tails.

Source: webcampi/package/pisight-mic/voice-filter.h, pcm_pisight_voice.c,
pisight-mic.mk and board/raspberrypizero/rootfs-overlay/etc/asound.conf.
The plugin accepts capture only, S16 mono client, S32 mono slave, 48 kHz.

## Verification

- Unfiltered baseline fails 10 filter-response/DC assertions as expected.
- Native and ARM1176-emulated DSP tests pass: response at 10 frequencies,
  DC rejection, silence, stream reset, impulse and saturation behavior.
- Independent analytical Butterworth magnitude expectation: within 0.12 dB
  across 20 Hz–20 kHz. Measured corners approximately -3.01 dB at 80 Hz/8 kHz;
  1 kHz approximately -0.001 dB.
- Native undefined-behavior sanitizer passes. AddressSanitizer invocation on
  this Mac stalled without results and was terminated; no ASan success claimed.
- Actual production transfer callback tested on ARM: nonzero offsets, padded
  and unaligned areas, LE conversion, bounds, fractional S32 precision, split
  blocks, reset and rate guard. Silent tails tested with block sizes 1–8192.
- Real target ALSA library dynamically loads the exact plugin extracted from
  the image. Synthetic stereo S32 hardware drives the repository route.
  17/1024-frame reads and same-handle drop/prepare with 513-frame reads produce
  identical 96000-sample outputs. Unsupported rates/channels rejected.
- All 96000 ARM capture samples match the native DSP reference exactly.
- Existing mic supervisor lifecycle tests pass (five scenarios).
- Independent code review found no production blocker; its silence and
  same-handle restart coverage requests are addressed.
- Full Buildroot image build passes. Hardware capture/CPU/subjective speech
  testing remains pending; emulation cannot establish Pi CPU headroom.

The test initially exposed two issues before completion. Per-state silence
cleanup could sustain an inaudible limit cycle; paired cleanup fixes the failing
ARM regression. ALSA file/null and a first RW synthetic source produced corrupt
partial-read fixtures even with the unfiltered baseline. The final mmap fixture
anchors data to committed appl_ptr and removes that test-source error. Neither
fixture is shipped. Preserved early failure logs are diagnostic history, not
final test results. packaged-arm-tests.txt contains the final integration result.

The earlier emulator-only DSP benchmark was 0.518 CPU seconds per 100 audio
seconds. This is NOT a Pi performance prediction and excludes ALSA/USB overhead.

## Existing recording

Applied the filter offline to capture-camera-work-20260928/microphone.wav.
Input and output both 5090304 samples, no clipped samples. RMS -36.21 -> -57.22
dBFS, peak 11853 -> 3585 PCM counts. This confirms substantial removed energy;
there was no controlled speech stimulus, so it does not prove improved speech
quality or diagnose prior mixed subjective feedback. Output is
existing-recording-filtered.wav. No sound was played and no new recording made.

## Image

File: diagnostics/sdcard-bandpass.img
Size: 41423360 bytes
SHA256: 71e0ce2413028c196f40ac97aa4b58df0ea20de84485a999c890e9f0baa03637

Baseline: sdcard-camera-work.img (95ecfd3891d2462178578b7b4f1b33cbe9a2c4c2806867ecf481cb14bdbec267).
verify-bandpass-image.py checks compiled source hashes, embedded squashfs and
root inventory. Exactly two changes: /etc/asound.conf and new
/usr/lib/alsa-lib/libasound_module_pcm_pisight_voice.so. Entire FAT boot partition
and kernel preserved byte-for-byte. All other root files match, including the
supervisor binary, camera libraries, shutter and diagnostics. Test fixtures absent.

Plugin SHA256: a79cc5f26ddc4e4b2d8c300b8968e960fd8b37ff632f4e8ffd632c3b817da35a.
Export/root: /private/tmp/pisight-bandpass. Docker volume contains final source
and build. No physical drive writes, serial access, live device changes, commits
or pushes. User alone flashes. The running Pi still has the previous image.

## Reproduction

Native: compile filter-test.c with cc -O2 -ffp-contract=off -std=c99, include
webcampi/package/pisight-mic, link -lm, then execute. Add -fsanitize=undefined
for the native sanitizer run. -DBASELINE selects the old pass-through behavior.

ARM tests use Buildroot's arm-linux-gcc and target libasound. The preserved
/work/bandpass/incoming/diagnostics/bandpass-tests/run-arm.sh runs against the
extracted image root and /work/bandpass/asound.conf synthetic hardware fixture
inside pisight-emulation:arm64. Tests do not access real devices. Full build logs
and exact image verification are alongside this report.

References: https://www.w3.org/TR/audio-eq-cookbook/ (coefficient formulae),
https://www.alsa-project.org/alsa-doc/alsa-lib/pcm_external_plugins.html (extplug).
