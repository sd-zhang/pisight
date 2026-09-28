# PiSight pre-flash code audit — 2026-09-27

**Implementation follow-up:** The defects below have now been corrected in source
and covered by regression tests. This report preserves the original findings;
see `audit-fixes-progress.md`, `audio-fix-results.md`, and `encoder-fix-results.md`
for implementation and verification. The old `sdcard-mic-gating.img` remains
withdrawn; it does not contain these corrections. Replacement `sdcard-audit-fixes.img` has passed build, regression, review and
artifact checks; its verification and hardware limits are in DEBUGGING_NOTES.md. No hardware performance claim follows from these software tests.

**Disposition: HOLD `sdcard-mic-gating.img`.** Its build and packaging checks
passed, but the broader integration audit found defects those tests missed.
Do not ask the user to flash this image as the next fix. Production source,
images, and physical drives were unchanged during this audit.

Scope: actual patched UVC/encoder source, kernel UVC/UAC2/DWC2 and videobuf2
paths, ALSA bridge, supervisor lifecycle, boot/settings scripts, and existing
hardware evidence. Review includes two independent read-only audio/encoder
reviews. Findings below distinguish deterministic code defects from unproven
explanations of the observed frame rate and audible delay.

## Findings requiring correction before another image recommendation

### P1 — Saved settings are not exported at startup

Both `webcampi/package/uvc-gadget/S60uvc-gadget:19` and the diagnostic overlay
`webcampi/board/raspberrypizero/rootfs-overlay/etc/init.d/S60uvc-gadget:19` use
`set -a; . /run/isight.env; set +a`. Actual BusyBox 1.37 hush rejects both `-a`
and `+a`. Variables become shell-local; the child gadget script and camera
process do not receive them. Consequently `microphone:false` can still expose
UAC2, and configured resolution/FOV/EV/quality can fall back to defaults.
The shell-local logo argument is a separate path and can still work.

Reproduced using the same BusyBox configuration compiled for the Linux host:

```
busybox sh -c 'set -a; ISIGHT_MICROPHONE=off; set +a; /usr/bin/printenv ISIGHT_MICROPHONE'
# exit 1, no stdout; both set operations report invalid option
busybox sh -c 'ISIGHT_MICROPHONE=off; export ISIGHT_MICROPHONE; /usr/bin/printenv ISIGHT_MICROPHONE'
# exit 0, stdout: off
```

Correct both installed-script sources using supported explicit exports, then
test loading a real generated environment into child processes. Prior testing
of the save script's `set -u` fix did not cover this boot path. This provides
a concrete explanation for the earlier ineffective microphone-off boot test.

### P1 — Gating can leave the mic stopped after USB resume

Kernel `f_uac2.c:1516` calls `u_audio_suspend()`; `u_audio.c:785` clears activity.
The callback table at `f_uac2.c:2290` registers suspend but no resume. The
supervisor at `webcampi/package/pisight-mic/pisight-mic.c:128` stops on rate 0
and cannot restart until the rate is 48000 again.

Trigger: host suspends and resumes the existing configuration/alternate setting
without a new SET_INTERFACE. Nothing restores active=true, so Playback Rate
stays zero. Fresh SET_INTERFACE/reset/re-enumeration can recover; this is not
an assertion that every replug fails. The source transition is missing;
occurrence on this Mac has not been tested. Cover resume with an active and
inactive alternate setting before relying on this control for lifecycle.

### P1 — Failed encodes submit a full stale buffer instead of dropping

`mjpeg_encoder.cpp:166–185` logs "frame dropped" but forwards bytesused=0.
The callback chain through `libcamera-source.cpp:103`, `stream.c:83`, and
`v4l2.c:817` queues it to UVC. Built `videobuf2-v4l2.c:298–306` substitutes the
allocated buffer length for zero; UVC never enables allow_zero_bytesused.
Tracked patch anchor:
`webcampi/package/uvc-gadget/0003-add-bcm2835-hardware-mjpeg-encoder.patch:692`.

Executed the extracted kernel branch in a compiled C check: all 3 expectations
confirmed. With length1843200 and zero bytesused, output becomes1843200;
normal34667 stays34667; explicit allow_zero retains zero. An encode failure
can therefore send stale/invalid JPEG contents rather than no image.
Current logs do not prove this failure path occurred. A fix must discard the
failed output while releasing both camera and destination-buffer ownership
and preserving the encoder output sequence; setting zero alone is insufficient.

### P1 — Codec-reported corruption is silently sent as a valid frame

`hw_mjpeg_encoder.cpp:424–437` ignores V4L2_BUF_FLAG_ERROR and copies nonzero
payload regardless. Actual bcm2835 codec `bcm2835-v4l2-codec.c:1232–1256`
converts MMAL CORRUPTED into VB2_BUF_STATE_ERROR with a payload; videobuf2
exposes the ERROR flag. Tracked patch anchor: `0003...patch:478–490`.

This path emits no existing encode-failure warning. It could contribute to
JPEG failures, but no target counter currently establishes that it occurs.
Reject flagged output through the same safe frame-drop path and count it.

## Other concrete reliability defects

- **P2 — Partial codec queue errors do not reset outstanding buffers.**
  `hw_mjpeg_encoder.cpp:382–427` can return after OUTPUT QBUF succeeded but
  CAPTURE QBUF failed, leaving OUTPUT index0 queued and configured_=true.
  Subsequent frames requeue the occupied index. Recover both queues and held
  DMA-BUF ownership before accepting another frame. No occurrence established
  in the supplied log.
- **P2 — Encoder shutdown can block indefinitely.** Blocking DQBUF at
  `hw_mjpeg_encoder.cpp:411,424` cannot be interrupted by the destructor:
  `mjpeg_encoder.cpp:63–70` joins workers before hardware teardown/STREAMOFF.
  A stalled codec can hang stream-off/reopen. Need bounded, cancellable waits
  and teardown tests, not just a shutdown flag.
- **P2 — Cross-thread state has data races.** `libcamera-source.cpp:92` pushes
  completed_requests while the main loop reads/pops it at130–134 without a
  mutex. Pipe notification does not protect a later concurrent push. Encoder
  abort flags are plain bools; destructor writes are not synchronized with
  worker reads. Source-confirmed races; no runtime race reproduction performed.
- **P2 — Rapid close/reopen may retain stale audio.** Supervisor drains pending
  events at148–149 and reads final state only. The compiled supervisor with the
  existing fake backend retained the same live child after a combined `b'01'`
  close/open. Ordinary separated transitions pass. The current ALSA rate event
  provides current state, not historical rate values; account for this limit
  before promising fresh buffers for every session.

## What this image does and does not establish

Sustained-idle gating is a valid response to the measured ~30% CPU waste and
full inactive playback buffer. Normal successful encoder buffer ownership also
looks sound: source frames remain owned through UVC dequeue, hardware output
is copied before reuse, and encoder teardown precedes source-buffer freeing.

Active audio still uses maximum SCHED_RR priority, 200ms hardware rings,
50ms startup priming, and the same recovery/synchronization algorithm. Ring
capacity alone is not latency, but one active target snapshot already had
7584 queued samples (~158ms). Gating supplies no active-backlog watchdog and
cannot be called a verified active-session delay fix.

The unchanged USB path still produced JPEG errors only while microphone
capture was open in the controlled test. No new code proves that cause fixed.
The -ENODATA recovery patch also changes missed-transfer reporting from warning
to debug, so absence of the old warning does not prove transfers stopped being
missed. Add bounded counters for missed USB transfers and for encoder errors,
and per-stage frame timing, before interpreting the next device run.

Existing four supervisor tests pass but omit suspend/resume and coalesced
transitions. Build success and rootfs/checksum validation establish artifact
integrity, not these missing behaviors. The image is held pending corrections
and expanded offline tests; no additional flash was requested by this audit.

## Evidence locations

Actual patched userspace sources:
`/private/tmp/pisight-stream-source/uvc-gadget-v0.4.4/lib/`.
Actual kernel/ALSA source excerpts:
`/private/tmp/pisight-stream-source/linux-custom/drivers/usb/gadget/function/`
and `/private/tmp/pisight-stream-source/alsa-utils-1.2.13/alsaloop/`.
Full built sources are in Docker volume pisight-build-work-amd64 under
`/work/buildroot/output/build/`; access read-only for audit. Matching host hush:
`/work/diagnostics/busybox-native-src/busybox`. Target evidence:
`diagnostics/target-uvc-recovery.log`, `recovery-target-cpu.json`, and
`uvc-recovery-host-results.json`.
