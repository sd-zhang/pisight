# Event-driven status LEDs

The user authorized further trimming while keeping diagnostics. The previous
`isight-logo activity` shell worker read GPIO 24, wrote GPIO 23 and slept once
per second. The new gadget patch 0019 drives both LEDs from existing stream
and settings events; there is no timer, GPIO read or additional worker.

The stream stores the configured logo mode during `uvc_open`. GPIO initializes
both outputs low; callback registration after successful GPIO initialization
applies off/on/activity immediately. STREAMON/STREAMOFF update activity, and a
successfully persisted XU settings request applies the new logo mode immediately.
The streaming indicator continues to follow stream state independently of logo
mode. The boot service no longer launches `isight-logo`, and that helper is
removed. Settings through isight.json/UVC are retained.

This change does not touch encoder dequeue pacing, USB scheduling, pigpio DMA
sampling, microphone supervision, or diagnostics. The existing pigpio -m change
still disables its alert thread; this LED change does not remove pigpiod itself.
No target CPU savings have been measured. This is a small avoidable-work cleanup,
not proof of fixing simultaneous microphone/video performance.

## Validation

- `check-led-events.py` exercises production stream function bodies, with camera
  start/stop and GPIO I/O stubbed: all modes at startup, repeated stream cycles,
  live setting changes while active/idle, and absent GPIO pass. It extracts
  verbatim functions to run on macOS; it does not simulate USB or physical LEDs.
- `check-gpio-led-only.py` compiles actual gpio.c: both two-pin and legacy
  three-pin arguments initialize low, toggle and clean up without input reads.
- Existing settings integration under the target-configured BusyBox fixture
  passes for both boot scripts, environment inheritance, successful persistence
  and failed JSON update cleanup. See `led-settings-tests.txt`.
- Independent source review found no introduced blocker. Its stale overlay-file
  caution was handled by explicitly deleting the old helper from the incremental
  target and verifying it is absent from SquashFS.
- Full incremental ARM build exited 0 (`build-led-events.log`). It reports the
  pre-existing unused `pu_control_name` warning and four Buildroot inventory
  notices. All five compiled source hashes match tested source; standalone patch
  application reproduces those source files exactly.
- `verify-led-events-image.py` verifies export hashes, embedded rootfs/kernel,
  root inventory and boot file content. Exactly four root paths differ from
  sdcard-camera-cpu-fix.img: service, gadget executable, gadget library, deleted
  helper. All boot files and other root files (including diagnostic services,
  microphone binary, and camera libraries) are unchanged.

## Artifact

`sdcard-led-events.img`: 41419264 bytes, SHA256 `fef43927dda8e11f6d38ef9b16a3da2f8367909aa2c75dabdec5f13d53facbf5`.
It includes camera log filtering, shutter removal, pigpio -m and exact
`iSight Microphone` naming in both alternate settings from earlier candidates.
Hardware untested. The user alone flashes; no physical drives were written.

Sources and exports: `/private/tmp/pisight-led-events/{base,new,export,root}`.
The Docker build volume already has patch 0019 applied; do not apply it twice.
No active build. Current physical Pi still has the earlier patch 0009 image.
