# Tests, measurements and historical investigations

Current status: [accepted baseline](../DEBUGGING_NOTES.md).
Latest hardware evidence: [audio settings run](capture-audio-settings-20260928/results.md).
Firmware verification: [audio controls checks](audio-controls-tests/results.md).
Protocol for the future app: [UVC controls](../docs/uvc-audio-controls.md).

This directory contains source tests and written reports. Images, raw captures,
recordings, generated summaries, compiler output and executable probes are local
artifacts excluded from Git. Reports referring to these files describe retained
local evidence; cloning the repository does not download it. Historical reports
can describe failures or withdrawn candidates; their dates and scopes matter.

## Offline checks from the repository root

The following use a host C compiler, Python 3 and a POSIX shell; no hardware or
physical drives are accessed:

```sh
python3 diagnostics/check-mic-supervisor.py
python3 diagnostics/check-diagnostic-log.py sh
python3 diagnostics/audio-controls-tests/check-diagnostics.py sh
```

The `audio-controls-tests/dsp.c` and `control.c` tests compile against
`webcampi/package/pisight-mic`. The control test needs temporary overrides for
`AUDIO_RUNTIME_PATH`, `DIAGNOSTICS_RUNTIME_PATH` and `CONFIG_STORE_PATH`; its
store fixture must sleep briefly and return `TEST_STORE_FAIL` when set. Never
point the host test at a real firmware settings writer. `areas.c` and `live.c`
use the real ALSA plugin callback and need ALSA development headers/libraries.

`audio-controls-tests/build-tests.sh` and `run-arm.sh` describe the existing
`/work` Linux build-volume layout and the earlier synthetic ALSA fixture. They
are environment-specific integration helpers, not a standalone fresh-clone
setup. ARM1176 emulation verifies computation and ALSA behavior, not USB timing.

For settings shell integration, use the project's BusyBox **hush** configuration
and real jq, rather than assuming desktop Bash behaves the same:

```sh
python3 diagnostics/check-settings-integration.py /path/to/busybox /path/to/jq /absolute/path/to/webcampi
python3 diagnostics/check-settings-shell.py /path/to/busybox webcampi/board/raspberrypizero/rootfs-overlay/usr/bin/isight-config-store
```

## Checks requiring patched Buildroot sources

Pass the source from the build that will actually be packaged. Examples:

```sh
python3 diagnostics/check-audio-arm-sof.py /path/to/linux-custom/drivers/usb/dwc2
python3 diagnostics/check-incomplete-defer.py /path/to/linux-custom/drivers/usb/dwc2
python3 diagnostics/check-dwc2-coalesced.py /path/to/linux-custom/drivers/usb/dwc2/gadget.c
python3 diagnostics/check-irq-sampling.py /path/to/linux-custom/drivers/usb/dwc2
python3 diagnostics/check-uac2-resume.py /path/to/linux-custom/drivers/usb/gadget/function
python3 diagnostics/check-led-events.py /path/to/uvc-gadget-v0.4.4
python3 diagnostics/check-shutter-stream.py /path/to/uvc-gadget-v0.4.4
python3 diagnostics/audio-controls-tests/check-routing.py /path/to/uvc-gadget-v0.4.4
python3 diagnostics/audio-controls-tests/check-descriptor.py /path/to/uvc-gadget-v0.4.4/scripts/uvc-gadget.sh
```

Older `check-audio-arm.py`, `check-audio-arm-one.py`, and the original
`usb-log-regression/check-control.py` / `check-descriptor.py` encode earlier
implementations. Use the SOF and audio-controls variants for this baseline.
The held endpoint-interval patch is historical and is deliberately outside the
production patch directories. Do not reintroduce it during cleanup.

Image verifiers compare extracted root filesystems and boot partitions with
previous local candidates. Their `/private/tmp` paths and baseline hashes are
part of that historical audit, not portable test dependencies available in Git.

## Hardware measurements

`run-concurrent-capture.sh OUTPUT_DIRECTORY` uses macOS AVFoundation to capture
720p video for 150 seconds, opening `iSight Microphone` for the middle 120 seconds,
then records a separate 20-second native combined session. It uses the camera
name, not an unstable AVFoundation index. It records audio; it does not play
sounds or write a physical drive. It needs Swift, FFmpeg and capture permission.

**Enable diagnostics temporarily through UVC first** if target snapshots are
needed. The shell script does not enable the new flag. Its readback uses Homebrew
libusb at the current local path in `read-usb-diagnostics.py`; adapt that path on
another host. No USB serial is needed. Restore diagnostics off after testing.
The latest `capture-audio-settings-20260928/hardware-test.py` is the one-off harness
used for live controls and restoration, with local paths and expected defaults;
review/adapt it before rerunning rather than treating it as a product CLI.

Summarize a capture with `summarize-concurrent-capture.py OUTPUT_DIRECTORY`.
Target helpers inspect PCM queues, IRQ snapshots and endpoint deltas. Bulk log
readback can temporarily reduce video FPS, so keep it outside baseline windows.
Do not call continuous timestamps an acoustic latency measurement.
