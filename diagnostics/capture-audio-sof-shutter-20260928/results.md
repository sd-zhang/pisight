# Combined audio SOF + shutter image: hardware test — 2026-09-28

The combined image maintains approximately 30 fps while capturing the microphone.
No sustained performance regression from enabling the shutter was observed in this
run. Rare video transport misses persist. Physical close/open switching and
acoustic microphone delay were not tested.

User reported flashing the new image. Candidate: `../sdcard-audio-sof-shutter.img`,
SHA256 `2dd46f63008959fae2be32bc008ad6377e37f7466640f86043601edf818b608a`.
The running image was not independently hashed. Readback confirms the expected
`interval=8 lead=1 timer_lead=2 sof=1` policy and `/usr/bin/uvc-gadget ... -S`.
Startup reports `Shutter: open, USB connected`; GPIO26 edge IRQ count remains zero
in all saved snapshots. This verifies initial open-state setup, not physical
sensor response or reconnect behavior. USB enumerated at 480 Mb/s; the microphone
was successfully selected by its exact name, `iSight Microphone`.

## Host measurements

| Measurement | Previous audio-SOF image | Combined shutter image |
|---|---:|---:|
| Mic-on distinct FPS | 29.959 | 29.969 |
| Mic-on JPEG errors over ~117 s | 5 | 5 |
| Video payload misses, first two sessions | 10 | 8 |
| Disabled video payload misses | 0 | 0 |
| Full active window CPU busy | 68.831% | 68.409% |
| Full active window incomplete IRQ/s | 0 | 0 |

150-second video test: microphone active for the middle 120 seconds. Trimmed
before/on/after windows are 6.557/116.709/14.086 seconds, with distinct FPS
30.224/29.969/29.962 and JPEG errors 0/5/1. The short initial arrival-based estimate
above 30 reflects delivery timing, not a higher camera frame rate. Overall 4485
unique images from 4485 callbacks; PTS-based FPS 29.952. Maximum mic-on changed
image gap was 157.835 ms versus 78.089 ms previously, so this run does not establish
identical frame pacing even though average throughput is unchanged.

20-second native simultaneous capture: 597 unique images from 599 callbacks,
PTS-based FPS 29.948; 960908 audio samples at 48 kHz spanning 20.0189 seconds,
zero audio PTS gaps over 1 ms. Maximum video arrival gap was 349.281 ms; arrival
and media timestamps measure different things and host batching is possible.
The two host decoder sessions report 6 and 1 dropped images respectively.

After USB diagnostic readback, a 30-second native simultaneous capture delivered
892 unique images from 900 callbacks (8 consecutive repeats), 29.806 distinct FPS
and 29.959 PTS-based FPS. Audio: 1440768 samples at 48 kHz over 30.016 seconds,
zero PTS gaps over 1 ms. No persistent large FPS degradation observed. One further
video NAK payload miss; no disabled video payload loss or late audio enable.

The FFmpeg WAV has varying nonzero signal, 107.157 seconds of samples across its
120-second timestamp capture, consistent with prior host FFmpeg behavior. Native
sample accounting is continuous. This is not proof of lossless audio, subjective
sound quality, or measured sound-to-host delay.

## Target evidence

The full simultaneous snapshot window spans uptime 68.18–132.60 s (64.42 s).
CPU busy 68.409%, gadget IRQ rate 8733.437/s, handler elapsed 13.152%.
Video completions 7993.527/s; audio 999.208/s. Incomplete IRQ and audio NAK deltas
are both zero in this window. Snapshot reads are sequential and include logging
overhead; rates are approximate.

First two sessions: 8 video payload misses, all NAK, and 43 empty misses. UVC
session summaries 7/31 and 1/12 payload/empty exactly reconcile these counters.
Host JPEG error count is 7; do not equate each USB payload failure with a distinct
host frame. The first video NAK at uptime 35.820562 s precedes microphone startup.
Four incomplete events select audio at closure or empty video requests; no video
payload loss through endpoint-disable recovery, and no deferred recovery needed.

Audio: 140304 scheduled and armed, zero late/early/cancelled/resync; 139722 SOF
waits/callbacks/arms. The two audio NAKs at 47.488450 and 186.883000 s precede PCM
capture triggers at 47.540279 and 186.944465 s. Two disabled audio events coincide
with closure. Post-readback capture adds 30107 scheduled/armed, still no late or
early enables, one audio NAK and one audio disabled event. Without another saved
PCM snapshot, the final NAK's precise relationship to PCM startup was not checked.

Encoder final counts 4497 and 604 frames, all failed/corrupt/invalid/timeouts/resets
zero. Source completed 4496 and 603, no drops. Long-session ALSA bridge CPU 4.583%;
combined capture/playback queues 45.583–50.333 ms, median 49.281 ms. These queue
readings exclude host and other stages and are not acoustic latency.

## Evidence and limits

Raw host and target logs, summary.json, irq-windows.json, transport-summary.json,
reconciliation.json, post-readback-combined.json, post-readback-counter-delta.json,
and run-context.json are preserved here. Scene/exposure and host load were not
controlled across runs. Initial shutter state works; close/reopen and suspend/
resume remain untested. No source changes or new image needed for these results.
No USB serial, physical-drive writes, card extraction, or sound playback. All
capture sessions finished.

- target.log SHA256: `1ae7d519facadcfe348b4f9489fac5edc7ddef48f7f87a9caa9071a299e464bb`

- target-usb-counters.log SHA256: `8b5b4eb8067d15e1af75e4f025d37b88c79bbdfa740c7dc1fecc321a85f11aae`

- post-readback-usb-counters.log SHA256: `fda8815a64db376938adf272cf98643110409e63fb269b8b9f282c5de607832a`
