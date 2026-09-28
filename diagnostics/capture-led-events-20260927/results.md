# CPU cleanup hardware result — 2026-09-27

**Large improvement, but not yet error-free simultaneous A/V.** At 1280×720/30,
mic-on video rose from 20.594 to 29.392 distinct fps; measured active CPU dropped
from 94.888% to 69.552%. Remaining USB/video corruption was not materially fixed.

Candidate: `../sdcard-led-events.img`, SHA256
`fef43927dda8e11f6d38ef9b16a3da2f8367909aa2c75dabdec5f13d53facbf5`.
The host sees **iSight Microphone** and captures it successfully. Target process
snapshots confirm pigpiod `-t 0 -m` and no isight-logo worker; the USB timing policy
is still interval=8/lead=3. Exact running image hash was not independently read.

## Host capture

| Measurement | Previous audio-arm image | Combined cleanup image |
|---|---:|---:|
| Mic-off video before | 24.593 fps | 29.988 fps |
| Mic-on video | 20.594 fps | 29.392 fps |
| Mic-off video after | 25.605 fps | 29.929 fps |
| Mic-on JPEG decode errors | 74 | 69 |
| Max mic-on changed-image gap | 263.176 ms | 105.293 ms |
| Native combined 20-second distinct fps | 20.640 | 29.406 |
| Post-readback combined 30-second fps | 19.600 | 29.478 |

Stable before/on/after windows lasted 9.654/116.521/11.186 seconds. JPEG errors
were 0/69/1 respectively. The native combined test delivered 586 distinct images
from 598 callbacks (12 repeats), and 960512 audio samples at 48 kHz without a
PTS gap over 1 ms. The later combined check delivered 881 distinct images from
899 callbacks and 1440768 continuous audio samples. No persistent FPS collapse
was observed after diagnostic readback in that 30-second check.

The long FFmpeg WAV contains 106.955 seconds of samples over its 120-second PTS
window, consistent with host capture sample loss seen in prior runs. It is not
proof of target PCM loss; both native combined captures have continuous audio
PTS/sample accounting. The WAV has varying nonzero audio. Neither check measures
acoustic sound-to-host delay or subjective microphone quality.

## Target evidence

Full simultaneous target snapshot interval: uptime 68.21–132.71 (64.5 seconds).
USB endpoint completion rates were approximately 7999 video/s and 1000 audio/s,
confirming sustained overlap across the interval.

- Total CPU busy: 69.552%, previously 94.888%.
- pigpiod thread runtime: approximately 0.002% total, previously about 11% in its
  busy alert thread. The alert-monitor CPU waste is removed in this run.
- Gadget IRQ rate: 9689.659/s; incomplete IRQ: 1000/s; handler elapsed: 13.304%.
  Previous values were 9732.721/s, 996.925/s and 13.206%: no meaningful reduction.
- Two busy camera-side threads now consumed 19.310% and 14.576% runtime, waiting
  13.407% and 12.125% respectively on the run queue. Thread role attribution beyond
  explicit CameraManager identification is inferred; see thread-costs.json.
- Audio bridge approximately 5.14% CPU over its long session. Sequential ALSA
  capture+playback queues 43.833–71.104 ms, median 49.615 ms; not acoustic latency.
- Encoder completed 4492 and 603 frames with zero failures, corruption, invalid
  frames, timeouts or resets. Source completed 4491/602, with zero source drops.
- Video missed payloads: 80 disabled + 9 NAK = 89, versus 93 previously. Empty
  misses: 41. These reconcile exactly with UVC summaries 79/36 and 10/5.
- Deferred requests: 24, all completed; zero forced recovery.
- Audio timers: 140192 scheduled and armed; zero late/early/cancel/resync.
  Maximum lateness accounting: 102 microseconds. Audio disabled events coincide
  with closure; no active-window audio NAK/selected events.

The cleanup provides CPU headroom and near-30-fps camera delivery while audio is
active. Similar remaining USB failures despite that headroom support treating
transport reliability as a distinct remaining issue. This is not evidence that
all CPU costs, audio latency, or USB timing defects are resolved. Because several
cleanups shipped together and scene/exposure were not controlled, the exact FPS
contribution of each change cannot be isolated from this run.

Snapshot collection is sequential; CPU/IRQ percentages are approximate and
include diagnostic overhead. Thread and IRQ accounting overlap and must not be
summed as disjoint CPU costs. Main target logs exclude the later post-readback
capture. No USB serial, card extraction, physical-drive writes or acoustic
chirps were used. Diagnostics remain enabled. No new image was built this turn.

## Evidence

See summary.json, transport-summary.json, irq-windows.json, thread-costs.json,
reconciliation.json and post-readback-combined.json in this directory.

- target.log SHA256 `07c77656fd212c72cdc0d808d06b02c59ce92e702ac646f1f392e6dfc0ae9430`
- target-usb-counters.log SHA256 `f66270b3fdb31021671894e46d0bed0ffebd52a869416ac0c18a442802b2a7c7`
