# Camera work optimization: hardware result — 2026-09-28

No meaningful CPU headroom improvement demonstrated. Simultaneous camera and
microphone still deliver approximately 30 fps. The measured 0.49 percentage-point
CPU reduction is smaller than variation among earlier runs; scene/exposure and
host load were not controlled. No new image or reflash is justified by this result.

Candidate: `../sdcard-camera-work.img`, SHA256
`95ecfd3891d2462178578b7b4f1b33cbe9a2c4c2806867ecf481cb14bdbec267`.
User reported replugging after candidate delivery; running bytes were not
independently hashed. Expected SOF scheduling policy is present. Physical shutter
state was not confirmed this run; the last explicit state was closed, while the
sensor reports open. This further limits small cross-run CPU comparisons.

## Comparable measurements

| Measurement | Prior SOF + shutter | Camera work candidate |
|---|---:|---:|
| CPU busy, full simultaneous interval | 68.409% | 67.922% |
| Mic-on distinct video FPS | 29.969 | 29.951 |
| Mic-on JPEG errors over ~117 seconds | 5 | 7 |
| First two sessions: video NAK payload misses | 8 | 18 |
| Video disabled payload misses | 0 | 0 |
| Active incomplete IRQ/s | 0 | 0 |
| Gadget IRQ handler elapsed | 13.152% | 13.141% |

Current full-active interval: uptime 129.45–193.79 seconds (64.34 seconds).
Gadget IRQ rate 8740.535/s, video completions 8005.642/s, audio 1000.730/s.
No active audio NAK delta. Snapshot reads are sequential, approximate, and include
diagnostic overhead. The following 64.475% CPU interval mixes active and inactive
capture and must not be used to claim an improvement.

Busiest camera threads: 18.642%, 14.420%, 6.790%, main 3.193%; previous
18.754%, 14.761%, 6.785%, main 3.351%. ALSA thread 4.782% versus 4.622%;
pigpiod 0.0021%. IRQ time overlaps thread attribution: do not add percentages.
Thread roles have not been established by stacks. Small changes are compatible
with savings but do not isolate the patches from ordinary workload variation.

## Host capture

150-second video capture with microphone open for the middle 120 seconds.
Trimmed mic-off/on/off windows: 29.805/29.951/29.971 distinct fps, JPEG errors
1/7/1 over 6.118/116.658/14.546 seconds. Overall 4479 unique frames from 4479
callbacks; PTS FPS 29.922. Maximum mic-on changed-image gap 131.713 ms.
Rare corruption persists; this run demonstrates no reliability improvement.

20-second native simultaneous capture: 593 unique images from 599 callbacks,
29.964 PTS fps; 960512 audio samples at 48 kHz over 20.010667 seconds, zero
PTS gaps greater than 1 ms. Host decoder sessions report 11 and 5 dropped images.

After diagnostic readback, 30-second native simultaneous capture: 898 unique
images from 899 callbacks, 29.943 PTS fps; 1440768 audio samples at 48 kHz over
30.016 seconds, zero PTS gaps greater than 1 ms. Maximum video arrival gap
86.539 ms. No lasting large throughput collapse observed after diagnostics.

## Target transport

First two UVC session summaries: 11/42 and 7/19 payload/empty misses. They exactly
reconcile endpoint totals: 18 payload, 61 empty; all payload misses use the NAK
path, zero disabled video payloads. First video NAK precedes microphone startup.
Four incomplete interrupts select audio at closure or empty video requests;
no recurring active incomplete interrupt pattern and no deferred recovery.

Audio: 140209 scheduled, 140208 armed, zero late/early/resync, one cancelled;
139524 SOF waits/callbacks/arms. Three audio NAKs: first at 104.802285 s before
PCM capture trigger 104.864971 s, last at 244.250078 s before second trigger
244.279984 s. The intermediate event timestamp is not retained; do not claim
all three are proven startup-only. Two disabled audio events coincide with closure.

Later counters show one additional video session and FOUR additional audio
sessions, not just our 30-second combined capture. Therefore the full delta is
not attributable exclusively to that check: +136230 audio schedules, +5 audio
NAKs, +4 disabled audio events. Source of the extra audio opens is unestablished.
Across that entire interval: zero additional video payload misses, zero late or
early audio enables, one additional cancelled arm. Raw counters are preserved.

Encoder final counts 4496 and 602, all failed/corrupt/invalid/timeouts/resets zero.
Source completed 4496 and 602 with zero drops. Long-session ALSA bridge CPU
4.833%; combined queue readings 46.5–72.646 ms, median 49.177 ms. Queue depth and
continuous timestamps do not establish acoustic latency or good microphone sound.
The reported rasping/sandpaper quality remains unresolved.

## Scope and evidence

Raw logs and generated summary.json, irq-windows.json, transport-summary.json,
thread-costs.json, reconciliation.json, post-readback-combined.json and
post-readback-counter-delta.json accompany this report. Hardware zoom/EV changes,
physical shutter switching, suspend/resume and acoustic latency were not tested.
No USB serial, physical drive writes, sound playback, source fixes or new image
this turn. Our capture processes have exited.

- target.log SHA256: `4166fab2798b04d11762134a396afb364415035da21b5b602f89a2d0e5c7d3b4`

- target-usb-counters.log SHA256: `3dc101b1359d1088c4a59345ee7c4b2a51550e7984787f302b7b539bec8e5873`

- post-readback-usb-counters.log SHA256: `11bfa018bedd92bce0cc8c025b129d51a5ae63f125635da5b13a0c07da8517fb`
