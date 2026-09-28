# UVC audio tuning and opt-in diagnostics — 2026-09-28

Built candidate: `diagnostics/sdcard-audio-settings.img`, 41,431,552 bytes.
SHA-256: `244a83b7ad1cad01d9df80f99996fda27e62de0b45a22f3fb88e0a0393186c39`.

Firmware only: existing UVC XU gains selectors 3/4, no new endpoint, serial,
web server, host CLI or app. Protocol: `docs/uvc-audio-controls.md`.
Audio gain ±24 dB in 0.5 dB steps, HP 20–500 Hz or off, LP 1–20 kHz in
100 Hz steps or off, bypass; defaults remain 0 dB/80 Hz/8 kHz/filter enabled.
Live changes use atomic shared RAM and a 20 ms crossfade; applied readback,
peak/clipping meters, RAM Reset and explicit asynchronous Save are implemented.
Save merges only the chosen category into the existing JSON with a shared writer
lock. Other settings survive. Capture timing and USB recovery are unchanged.

Diagnostics default off, controlled live through UVC and persisted on Save.
Enabled periodic snapshots remain in RAM at `/tmp/PISIGHT.TXT`, capped at 4 MiB,
with 256 KiB per append; readback remains on selector 2. Automatic diagnostic
copies/remounts to SD are removed. Raw I2S boot capture and detailed mic snapshots
respect the flag. Existing basic RAM process logs and USB recovery counters
remain; the cap covers the snapshot file, not every process log. Startup still
seeds/repairs absent/invalid config on SD. This is not a promise of zero SD writes.

## Verification

- Pi Zero ARM build and full Buildroot image build exited 0 (`arm-build.txt`,
  `image-build.txt`). Existing unused-function and Buildroot inventory warnings
  are unchanged, nonfatal.
- Native UBSan DSP/control tests pass. The old fixed filter fails the requested
  +6 dB behavior (`baseline.txt`); the new filter measures +6.0003 dB.
- ARM1176-emulated tests pass for gain/filter response, bypass, smoothing,
  saturation, quiet tails, real transfer offsets/strides, reset, arbitrary S32
  bypass boundaries, settings applied during a fade, readback and meters.
- UVC payload validation, async Save success/error, busy token preservation,
  diagnostics Apply/Save/Reset and cross-process atomic preset exchange pass.
- Actual production UVC setup/control code tests pass for old/new selectors,
  malformed lengths, wrong direction/interface and reserved wValue bits.
  Built descriptor fragment advertises four selectors with the existing GUID.
- Actual settings/init scripts with target-configured native BusyBox hush and
  real jq pass save/reload/default/invalid-input/error-cleanup/JSON-preservation
  and concurrent-writer-lock checks (`integration-build.txt`).
- Snapshot functions under BusyBox pass missing/off gating, live enable/disable,
  full 4 MiB rotation and cancellation when disabled during collection. Existing
  incremental mic-log reading remains intact (`diagnostics-hush.txt`).
- Mic supervisor six lifecycle scenarios pass, including diagnostics off.
- Real ALSA plugin and production route pass using a synthetic direct-MMAP I2S
  source with 17/1024-frame reads and same-handle prepare/restart. All 96,000
  default samples match the prior native reference prefix. Intentional wrong
  rate/channel tests reject them; their ALSA stderr is expected.
- Tests also pass with libraries extracted from the final SquashFS
  (`packaged-arm-tests.txt`).
- Image verifier checks exported hashes, compiled source hashes, script bytes,
  permissions, default diagnostics=false, and exactly 11 expected root changes
  against the fixed band-pass image. Boot file contents match; final image uses
  the previous boot partition byte-for-byte, including the unchanged kernel.
- Independent source review found no remaining blocker after fixing child-side
  snprintf before exec and float rounding at extreme S32 bypass values.
- Whitespace checks pass. No commits/pushes, hardware writes, serial, sound
  playback or live Pi captures were performed for this candidate.

## Limits / next hardware test

ARM emulation tests computation, control flow and actual ALSA plumbing. It does
not reproduce physical USB/DMA timing, CPU headroom, acoustic quality or host UVC
interoperability. This image has not been flashed or hardware-tested. Only the
user flashes. No additional physical test is required to deliver these firmware
capabilities; when testing later, enable diagnostics explicitly before expecting
periodic snapshots. Existing host capture scripts do not enable the new flag.

Build volume contains final sources/patch0022. Export/extracted files are in
`/private/tmp/pisight-audio-controls` and `/work/audio-controls` in the Docker
volume. `build-tests.sh` and `run-arm.sh` use that existing build environment and
the prior band-pass synthetic ALSA fixture. Export via tar stream; direct volume
copies through a Mac bind mount previously corrupted artifacts.
