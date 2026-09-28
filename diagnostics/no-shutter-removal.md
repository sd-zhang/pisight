# Shutter monitoring removed

User requested removal of the nonfunctional shutter monitor after the current
hardware run attributed approximately11% CPU to pigpiod. New candidate:
`sdcard-no-shutter.img`,41394688bytes, SHA256
`20b1ad04c5f7674d67d34fded498988956fc9186f40303e36e38bf3bbd5af9c5`.

Patch0017 removes sensor pin configuration/read, glitch filtering, edge callback,
and shutter-driven frame freezing. Host UVC controls streaming. Running and
streaming LEDs remain, with startup arguments23/24. Old three-pin arguments are
accepted but the third pin is ignored. The daemon starts with `-t 0 -m`.
Pigpio79 source confirms `-m` skips creation of the alert CPU thread. It still
initializes DMA and a PWM clock; `-t 0` remains necessary to leave I2S/PCM alone.
Its client notification thread blocks without registered callbacks. This is not
removal of every GPIO thread or DMA sampling operation.

A steady LED uses latched GPIO output. The existing rear-logo activity script
still reads the streaming LED once per second; that is separate from pigpio's
expensive alert worker. This change preserves existing logo configuration.

## Verification

- Actualgpio.c check with unavailable shutter input/alerts: baseline fails two
 cases; new two-pin and legacy-three-pin configurations pass LED startup,
 transitions and cleanup. `check-gpio-led-only.py`, `no-shutter-checks.txt`.
- Independent source review found no introduced blockers; reviewer reproduced
 baseline failures, passes, patch dry-run and shell syntax checks.
- ARM build exit0. Existing unused `pu_control_name` warning inuvc.c plus four
 known Buildroot `.files-list*.before` comm notices; no compile errors.
- Compiled source hashes match all five reviewed changed files.
- Packaged filesystem verification passes. Exactlyfour rootfs paths changed:
 `/etc/default/pigpio`, `/etc/init.d/S60uvc-gadget`, `/usr/bin/uvc-gadget`,
 `/usr/lib/libuvcgadget.so.0.4.0`. Boot files and kernel byte-for-byte unchanged.
- `verify-no-shutter-image.py`, `no-shutter-image-verification.txt` record the
 packaged-kernel/rootfs checks and export hash verification. No AppleDouble files.

Hardware CPU saving, simultaneous A/V improvement and physical LED behavior are
not yet measured. This is the requested feature removal, not a proven full FPS
fix. Acoustic latency is also unmeasured. Latest tested image remains patch0009;
see `capture-audio-arm-20260927/results.md`. No USB timing cleanup was bundled.

User alone flashes. No serial, physical-drive writes, commits or pushes.
Next capture should verify daemon arguments include-m, alert worker is absent,
and compare totalCPU, camera scheduling waits, distinctFPS, JPEGerrors and audio
continuity. Use existing UVC readback after capture, no card extraction.

Sources: `/private/tmp/pisight-no-shutter/{base,new}`. Active patch:
`webcampi/package/uvc-gadget/0017-remove-shutter-monitor.patch`. Build volume
contains the patch and applied sources; do not apply it twice on that tree.
