# Simple shutter USB switch

**Latest combined candidate:** `sdcard-audio-sof-shutter.img` now includes the
hardware-tested audio-SOF kernel plus this shutter implementation. User explicitly
requested inclusion on2026-09-28 despite suspected sensor trouble. See
[combined image notes](sdcard-audio-sof-shutter.README.txt). Hardware shutter
validation remains pending.

User approved a shutter that makes the device unavailable, without wasting CPU,
and asked to keep it simple. Patch `0020-shutter-usb-soft-switch.patch` adds one
GPIO edge watcher to the existing uvc-gadget process. No new service, worker,
periodic GPIO read, user-space timer, or libgpiod dependency is introduced.

The PiSight boot service passes `-S`. GPIO chip identity must be
`pinctrl-bcm2835`, line 26, high=closed and low=open. This polarity matches the
previous implementation and the [sensor author's measurements](https://github.com/elcalzado/isight-shutter).
The actual user's sensor has not been validated; the earlier nonfunctional
monitor does not prove its wiring or voltage behavior.

## Behavior

- Request one input line with rising/falling events and 50 ms kernel debounce.
- Before UVC setup subscription can activate the composite gadget, write
  `disconnect` to the bound controller's `soft_connect`. This keeps a closed
  shutter from advertising USB while application initialization proceeds.
- After UVC handlers are installed, read the initial level and connect only if
  open. The initial state does not require the user to toggle the shutter.
- On an edge, read the current debounced level rather than replaying stale queued
  levels. Duplicate states do not cause repeated USB reconnects.
- Closing blocks queued STREAMON requests, stops the video source/encoder, and
  software-disconnects the complete gadget. Kernel UAC2 disable stops its endpoints
  and clears playback activity; the existing microphone supervisor stops alsaloop.
- Opening reconnects the configured gadget and permits future host STREAMON.
  It does not start the camera or microphone without a host request.
- GPIO/sysfs failures stop capture and terminate the event loop. Closing the UVC
  application handle deactivates the composite gadget. There is no retry spin.
- Normal USB disconnect also stops video. Stops are idempotent so subsequent
  STREAMOFF or application cleanup does not free the same buffers twice.

The Pi stays powered, GPIO interrupts stay available while USB is off, and no
ConfigFS teardown or function recreation is needed. Apps may need to reopen
both devices after reconnection. UVC diagnostic readback is unavailable while
USB is disconnected; on-device diagnostic collection remains intact, including
the existing one-off raw I2S boot probe. This is a software switch, not removal
of electrical power from sensors or the Pi.

## Kernel and toolchain checks

The exact built kernel already has GPIO_CDEV v2; v1 is disabled. Its GPIO driver
supports IRQs and the GPIO core supplies software debounce when needed. The UDC
`soft_connect` path starts/stops DWC2 without unbinding UVC/UAC2. UVC function
disable emits DISCONNECT, and UAC2 disable stops playback/capture. The gadget
starts deactivated until the application subscribes to UVC setup events.

The ARM toolchain's older linux/gpio.h does not define v2, causing the first
build to fail. `lib/gpio-uapi.h` is an unmodified copy of
`include/uapi/linux/gpio.h` from pinned Raspberry Pi kernel commit
`cd231d4775b14f228606c09f219b48308f6ab3aa`; its original SPDX/copyright remain.
It adds compile-time declarations only. ABI assertions verify request size592,
fd offset588, config272, event48, values16 and both used ioctl numbers on ARM
and the native Linux test build. Header bytes match the exact built kernel.

Review identified that checking the existing start return while leaving active
false could bypass cleanup of partial starts. That extra behavior change was
removed, preserving previous cleanup semantics. A regression test first failed
and then passed: shutter close cleans partial startup exactly once.

The sysfs implementation does not propagate every internal controller error.
Write success proves command acceptance, not host enumeration. GPIO electrical
behavior, bounce handling on this actual sensor, CPU overhead, and repeated
Mac close/reopen still require hardware validation.

## Validation and image

- `check-shutter-stream.py`: close stops once, queued starts are blocked, reopening
  waits for host request, repeated events are idempotent, partial-start cleanup.
  Baseline fails; final source and clean patch application pass.
- `shutter-regression/check.c`: actual shutter.c with GPIO/sysfs/event registration
  boundaries substituted. Boot open/closed, transitions, duplicates, request/read
  failures and USB write failure pass. Native and ARM1176 QEMU runs pass; this does
  not emulate GPIO electronics or USB scheduling.
- Existing LED and LED-only GPIO tests, BusyBox settings/persistence checks, and
  both boot-script shell syntax checks pass.
- Independent lifecycle review completed; both findings above addressed.
- Full ARM build exits0. Final build has four pre-existing Buildroot inventory
  notices, no compiler warnings/errors. First failed build is retained separately.
- Nine compiled file hashes match reviewed source and clean patch application.
- `verify-shutter-switch-image.py` confirms exactly three changed root paths versus
  sdcard-led-events.img: S60uvc-gadget, usr/bin/uvc-gadget and libuvcgadget.so.0.4.0.
  Other root paths and all boot file contents are unchanged. Export hashes and
  embedded kernel/rootfs match. No physical drives were accessed or flashed.

Latest candidate: `sdcard-shutter-switch.img`, 41423360 bytes,
SHA256 `5634e3a8699b2944ebd9fd25fc42c27435c79a61ceed59a215c25b3f258c8a51`. Not hardware-tested. The prior tested LED-events image remains
available and is still the physical Pi's current firmware.

Build/source/export workspace: `/private/tmp/pisight-shutter-switch/`.
Docker volume has final patch0020 source applied; do not apply it twice. No build
is running. Runtime regressions and test logs are under diagnostics/shutter-*.
