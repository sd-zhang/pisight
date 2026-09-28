# Advertised video modes and software reboot — 2026-09-28

Candidate image: `diagnostics/sdcard-video-modes.img`, 41,431,552 bytes.
SHA-256: `4e82289ba85a661923176d8aeccd44fae868718edf548f4bc78404db3ed33ffc`.
Firmware source: `webcampi` commit `e5b3382` on `pizero-hw-mjpeg-encoder`.
No physical drive was written and the candidate has not been flashed or
hardware-tested. The enclosure is now sealed with the last confirmed installed
audio-settings baseline; the hardware check below is deferred.

## Change

UVC selector 5 selects any nonempty subset of 720p, 1080p and 1280×960. Selection
is in RAM; Save writes the existing `resolutions` JSON array. An explicit Save
and restart operation requests a normal software Pi reboot after successful
save and read-only remount, so no unplug is required to apply descriptor changes.
The future app must rediscover the device after boot; no host app was added.
See [protocol](../../docs/uvc-video-modes.md).

The implementation uses a full software reboot because the existing service
stop/configfs teardown is not reliable enough for a USB-only restart. A full
reboot releases the resources through kernel shutdown and rebuilds descriptors
through normal boot. Unsaved settings and RAM logs are lost. Ordinary resolution
selection within the existing advertised list uses UVC negotiation as before.

## Verification

- Native selector tests under undefined-behavior sanitizer: all seven masks,
  invalid masks and reserved fields, selected/saved/active readback, asynchronous
  save/error/busy tokens, reset defaults, boot reload, custom and reordered
  lists, explicit reboot helper arguments. Existing audio control tests pass.
- Actual patched UVC SETUP/control routing and video DATA dispatch compiled and
  exercised; bad lengths/directions/interface/value rejected. Executed descriptor
  fragment advertises all five controls with the unchanged GUID.
- Real configured BusyBox hush, jq and config-lock code: every subset saves and
  reloads while preserving other settings. The substituted reboot endpoint sees
  new JSON only after read-only remount and at least a one-second delay. Failed
  JSON generation and failed read-only remount suppress reboot. Reboot endpoint
  failure reports failure. Existing settings, invalid input and lock tests pass.
- ARM1176 emulation against the packaged root: video selector and audio controls,
  DSP, interleaved ALSA areas, live tuning, default filter response, real ALSA
  plugin split-read and same-handle restart checks pass. Unsupported format
  negative cases emit the expected ALSA errors.
- All six microphone supervisor cases and diagnostics logging/toggle/rotation
  regressions pass. Independent review found no blocking issue; its optional
  remount failure test was added and passed.
- Build succeeds. The image verifier confirms the boot partition is byte-for-byte
  the accepted audio-settings baseline, including the kernel. Exactly three
  packaged files differ: `usr/bin/isight-config-store`,
  `usr/lib/libuvcgadget.so.0.4.0`, and `usr/local/bin/uvc-gadget.sh`.
  Microphone binaries, DSP plugin, libcamera and USB scheduling are unchanged.
  Export hashes and compiled gadget source hashes match local files.

## Reproduce

From the repository root:

```sh
sh diagnostics/video-modes-tests/run-native.sh /path/to/patched/uvc-gadget
python3 diagnostics/check-settings-integration.py /path/to/configured/busybox /path/to/jq /path/to/webcampi
```

The ARM suite uses the existing Linux build volume and fixture paths documented
in `audio-controls-tests/build-tests.sh` and `run-arm.sh`. Compile `control.c`
with `CONFIG_STORE_PATH` set to that suite's store fixture and `STORE_CALLS_PATH`
to its call log, then run under `qemu-arm-static -cpu arm1176`. Never point tests
at the production settings writer. The image verifier uses retained baseline
and extracted roots under `/private/tmp` as earlier image verifiers do.

## Remaining hardware check

With the candidate flashed, select only 720p via selector 5, request operation 4,
wait for USB disappearance and return, and confirm only 720p is advertised and
selected/saved/active all read 1. Verify simultaneous camera and microphone
capture, then restore the desired set and apply once more. This has not been
performed. Offline success does not prove host descriptor cache refresh or
physical USB rediscovery, and no new FPS/latency claim is made.
