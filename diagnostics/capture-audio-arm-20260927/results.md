# Delayed audio enable hardware results — 2026-09-27

**Simultaneous A/V still fails the smooth-video goal.** Patch0009 reduces excess
interrupts and damaged video, but combined capture remains about 20.6 distinct
fps at 720p/30. Total CPU remains about 95%; acoustic delay is unmeasured.

Image: `../sdcard-audio-arm.img`, SHA256
`ae709600d0fe284c9e9d17bf0043271bb23d66177c2e4d48113087236941b5c2`.
Preflight readback reports `irq_arm_policy interval=8 lead=3`, confirming the new
code path. The exact running kernel hash was not independently read from the Pi.

## Capture

| Stable window | Distinct fps | JPEG decode errors |
|---|---:|---:|
| Before microphone | 24.593 | 0 |
| Microphone active | 20.594 | 74 |
| After microphone | 25.605 | 0 |

Before/active/after durations: 6.339/116.612/14.274 seconds. Maximum changed-image
gap with mic active: 263.176 ms. Native combined 20-second check: 410 distinct
images, 595 callbacks, 185 repeats, 20.640 distinct fps. Audio delivered 960512
samples at 48 kHz with no timestamp gap over 1 ms. See `summary.json`.

ALSA sequential queue snapshots: 43.854–72.917 ms, median 48.646 ms. The microphone
bridge consumed about 3.98% CPU. These queues and timestamp continuity do not
measure physical sound-to-host latency. The FFmpeg recording can lose samples
in its host input buffer and is not proof of target PCM loss.

## Transport and CPU

Full active target window 130.02–195.39 seconds (`irq-windows.json`):

| Measurement | Previous patch0008 | Patch0009 |
|---|---:|---:|
| Gadget IRQ entries/s | 12661.343 | 9732.721 |
| Incomplete IRQ/s | 3986.691 | 996.925 |
| Gadget handler elapsed fraction | 12.955% | 13.206% |
| Aggregate CPU busy | 94.809% | 94.888% |
| Failed video payloads, entire standard run | 322 | 93 |
| Mic-on JPEG errors | 220 | 74 |
| Native combined distinct fps | 17.724 | 20.640 |

Audio timers: 140190 scheduled, 140189 armed, one late callback, zero early,
zero cancelled, zero resync. Maximum lateness 359 us. In the full active window
there were no late callbacks or audio NAK/disabled misses; timer callback elapsed
time was 0.596% of that window. Elapsed time includes lock waiting, and timer
scheduling work can also run inside the IRQ handler. Lower IRQ count did not
produce a measured reduction in total CPU or gadget-handler time.

Video failures reconcile exactly: 79 disabled payloads +14 NAK payloads =93;
53 empty misses. UVC sessions report 88/41 and 5/12 payload/empty errors.
17 deferred requests all completed; none required recovery. See
`reconciliation.json`. Audio disabled events occur at microphone closure;
NAK counters include initial synchronization. The sole late timer's exact time
is not logged, so do not assign it to shutdown as a proven fact.

Encoder: 3289 and 435 completed frames, zero failed/corrupt/invalid/timeout/reset
results. Mean encode wall time approximately 13.3 ms includes dequeue waits.
Zero errors does not prove the entire camera pipeline supplies 30 fps.

Per-thread scheduling counters show CPU contention (`thread-costs.json`).
Two camera threads consume approximately 24% and 23% runtime while waiting on
the run queue for approximately 33% and 28% of elapsed time. pigpiod consumes
about 11%. These costs overlap interrupt attribution on this kernel and must
not be added to handler elapsed time as disjoint CPU percentages.

## Readback and remaining leads

30-second native combined check after diagnostic readback: 585 distinct frames,
897 callbacks, 312 repeats, 19.600 distinct fps. Audio: 1440768 samples with no
PTS gap over 1 ms. This is similar to the preceding combined performance, but
has a 296.626 ms maximum video arrival gap. It is not proof that readback cannot
affect performance. Main target logs exclude this later capture. No serial used.

After capture and before diagnostic readback, saved target snapshots show about
1000 unclassified IN endpoint IRQ/s, with no isochronous completion increments;
handler cost is only about 0.57%. Source suggests the UAC notification endpoint
plus a retained global NAK mask could account for this. Existing counters omit
nonisochronous endpoint causes, so attribution remains unproven. This is not an
established explanation of the active-stream FPS loss.

User subsequently authorized removing shutter monitoring. That is a separate
candidate; no such removal is included in the tested patch0009 image.

Snapshot collection is sequential and slow: rates/percentages are approximate
and include diagnostic overhead. No acoustic chirps were played. No physical
drives were written and no card extraction was required.

## Raw evidence

- `target.log` SHA256 `410d945b8e8b93490c7910bce5ffa27e1a8eabb4b26c294502f80ce19160cfaa`
- `target-usb-counters.log` SHA256 `a3de940e1da01b56ede95aa0c1cc2c64b1d7df333594bfe57a29cbc5b73fb6e7`
