# PiSight: accepted baseline and remaining work

The user accepted the tested baseline on **2026-09-28**. The objective is smooth
simultaneous camera and microphone operation, not another speculative image.
The user has sealed the enclosure. The last confirmed installed firmware is the
accepted audio-settings baseline; no installation of the video-modes candidate
was reported. Leave hardware testing deferred until the user chooses to reopen
or update it.

Local image: `diagnostics/sdcard-audio-settings.img` (41,431,552 bytes).
SHA-256: `244a83b7ad1cad01d9df80f99996fda27e62de0b45a22f3fb88e0a0393186c39`.
Firmware source is committed in `webcampi` as `9dd445f` on
`pizero-hw-mjpeg-encoder`. The image is a local build artifact, not a committed
file or published release.

## New candidate awaiting hardware verification

`diagnostics/sdcard-video-modes.img` adds selectable advertised presets through
UVC selector 5 and a Save-and-soft-reboot action, with no physical unplug needed.
Firmware source is `webcampi` commit `e5b3382` on `pizero-hw-mjpeg-encoder`.
The accepted image above remains the hardware baseline. Only the settings writer,
UVC library and gadget setup script differ; kernel/audio binaries are unchanged.
See [candidate verification](diagnostics/video-modes-tests/results.md) and
[app protocol](docs/uvc-video-modes.md). The UVC app is still future work.

## What is working

- 1280×720 hardware MJPEG with the microphone open: **29.960 distinct fps**,
  six JPEG decode errors over about 117 seconds. Previous working image:
  29.951 fps and seven errors. Rare corruption remains; the user accepts it.
- Native simultaneous captures of 20 and 90 seconds: continuous 48 kHz audio
  timestamps. Acoustic latency and subjective voice quality were not measured.
- Live UVC gain, high-pass, low-pass and bypass settings reached the audio
  processor and were read back. Audio defaults restored to 0 dB, 80 Hz–8 kHz.
- Diagnostics enable/disable works. The 173,542-byte RAM snapshot log remained
  identical 84 seconds after disabling. Diagnostics is off in RAM and saved
  config; no hardware Save request was issued during the test.
- Mic process CPU is about 9.1%, compared with about 4.8% before filtering.
  Total CPU was around 71–72% in mostly active windows; these are not an exact
  comparison with the previous fully active 67.9% interval.

Detailed evidence: [hardware report](diagnostics/capture-audio-settings-20260928/results.md).
Offline checks and image contents: [verification report](diagnostics/audio-controls-tests/results.md).
Future app protocol: [UVC audio and diagnostics](docs/uvc-audio-controls.md).

## Diagnosis and fixes retained in this baseline

Several defects overlapped; there was no single “bad cable” explanation.

1. Legacy audio gadget ownership initially prevented the composite camera from
   binding. The UAC2 direction also needed correction to expose a microphone.
2. pigpio's default PCM clock conflicted with I2S capture. Use `-t 0 -m`: PWM
   clock selection, with the continuous GPIO sampling worker disabled.
3. The audio bridge used CPU and accumulated queued audio even when the host
   was not listening. The ALSA-event supervisor now starts/stops it with capture.
4. DWC2 isochronous recovery could misattribute interrupt events and retire
   video requests prematurely. Ownership/age checks were corrected. Audio IN
   enable is aligned to the intended USB frame using a temporary SOF interrupt.
5. Suppressed libcamera debug formatting and GPIO polling consumed CPU that
   the Zero needed for streaming. Log filtering and event-driven GPIO/LEDs
   restored headroom. Later camera micro-optimizations showed no meaningful
   whole-device CPU improvement on hardware; do not overstate them.

These changes restored near-30-fps simultaneous operation. The kernel still
records occasional NAK payload misses. In the latest first two sessions there
were 11 video NAK payload misses, zero disabled video payload misses, and one
late audio arm out of 140,201 schedules. The old recurring interrupt storm did
not return. The hardware encoder reported zero failures/timeouts/resets.

## Diagnostics and known limits

Periodic snapshots stay in RAM, capped at 4 MiB; individual appends are capped
at 256 KiB. The cap applies to `PISIGHT.TXT`, not every basic process log.
Automatic SD log copies are removed. Explicit settings Save and initial config
seeding/repair still write to the SD card. Default diagnostics is **off**.

Downloading the full log during simultaneous capture briefly reduced distinct
video delivery to 23.9 fps in the affected ten-second window, with 14 JPEG
errors. It recovered to 29.964 fps for the following minute; audio timestamps
remained continuous. Avoid or throttle bulk downloads in the future app.
Small setting changes and bulk log transfers are different workloads.

Hardware Save/reboot persistence was not tested in the latest run; real JSON
scripts, validation, locking and failure cleanup passed offline. Filter response
and exact bypass conversion were tested natively and under ARM1176 emulation.
The 4 MiB rotation limit was tested offline. Neither emulation nor ambient WAV
levels prove acoustic quality, latency, or physical shutter operation.

The physical shutter sensor has not followed the shutter on this unit. The user
accepts a purely mechanical shutter; do not turn that into another required task.

## Where to go next

The firmware is ready for a future UVC settings app. Keep live adjustments in RAM
and Save explicit. The user has not requested an app implementation or another
flash. No serial/web interface is needed. No current capture or build is running.

For chronology and rejected hypotheses, see the
[engineering story](docs/the-road-to-simultaneous-av.md) and
[archived development log](docs/history/development-log-2026-09.md). The archive
contains superseded instructions and candidate statuses, not current guidance.
