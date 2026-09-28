# Frame-aligned audio enable: hardware result — 2026-09-27

**The targeted USB scheduling failure is substantially corrected.** During
simultaneous1280×720 video and48kHz microphone capture, video measured29.959
changed images/s, mic-on JPEG errors fell69→5, and endpoint-disable payload
loss fell80→0. The previous~1000 incomplete interrupts/s disappeared in the
fully active64.46-second target window. Some NAK video misses and one delayed
audio enable remain; do not claim error-free transport or measured acoustic delay.

The user flashed `../sdcard-audio-sof.img`, SHA256
`4e24ecde63ef34d3844cfee556c1c0c2906a68ccde075f13e81c7a087394f89a`.
Readback confirms `irq_arm_policy interval=8 lead=1 timer_lead=2 sof=1`.
Exact running image bytes were not independently hashed. Shutter physically
open; user suspects broken/miswired sensor. This image has monitoring disabled.
Keep it disabled in future reliability testing; the separate shutter candidate
has not been flashed/tested and should not be silently reintroduced.

## Host comparison

| Measurement | LED-events baseline | Audio SOF image |
|---|---:|---:|
| Mic-off FPS before |29.988|29.995|
| Mic-on FPS |29.392|29.959|
| Mic-off FPS after |29.929|29.735|
| Mic-on JPEG errors |69|5|
| Max mic-on changed-image gap |105.293ms|78.089ms|
| Video payload misses, first two sessions |89|10|
| Disabled video payload misses |80|0|
| Fully active incomplete IRQ/s |1000|0|
| Fully active CPU busy |69.552%|68.831%|

Stable before/on/after windows6.536/116.702/14.289seconds; JPEG errors0/5/4.
The150-second camera run delivered4484 distinct images with zero repeated-image
callbacks. The20-second native combined check delivered598 distinct images
from600 callbacks and960512 audio samples at48kHz, with no audio PTS gap>1ms.
The first two complete decoder sessions logged9+1 JPEG errors. These match the
9+1 UVC payload misses by count; that alone does not identify each packet.

After USB readback,30 seconds of simultaneous capture delivered899 distinct
images from899 callbacks and1440768 audio samples with no PTS gap>1ms. Video
was approximately30fps (arrival-based distinct estimate30.071; PTS-based29.959,
reflecting delivery timing rather than a changed camera mode). No persistent
post-readback slowdown observed. Post-readback counters added one video NAK
payload miss, zero disabled video payloads and zero additional late audio
enables. The one new audio NAK occurred at capture start; one audio disabled
payload occurred at closure, consistent with the first two sessions.

The FFmpeg WAV contains106.752seconds of samples over the120-second PTS capture,
as in earlier runs. It is not proof of target audio loss; native accounting
was continuous. The WAV contains varying nonzero microphone signal. Continuous
host timestamps do not exclude concealed USB loss, quantify subjective audio
quality, or measure sound-to-host acoustic delay.

## Target evidence

Fully simultaneous snapshots: uptime68.20→132.66,64.46seconds. Endpoint
completion rates~7993.33 video/s and999.18 audio/s; sequential snapshot timing
accounts for approximate rate estimates. CPU68.831%, gadget IRQ8770.354/s,
gadget handler elapsed13.102%. Previously69.552%,9689.659/s,13.304%.
CPU/handler costs are roughly unchanged; the demonstrated improvement is
transport reliability. Temporary SOFs can coalesce with other endpoint IRQs.

- Incomplete IRQ count0 and selected endpoint count0 in the full active window.
  Only5 incomplete causes across the initial two sessions, with selection
  samples at closure and empty video requests. No premature video recovery
  samples remain; no deferred recovery was needed.
- Video payload losses10, all NAK; disabled losses0. Empty losses57.
  UVC summaries9/38 and1/19 exactly reconcile payload/empty totals.
  First NAK at54.163s precedes audio startup at65.724s, establishing that some
  residual misses also occur with the microphone off. Do not attribute every
  residual NAK to audio scheduling.
- Audio scheduled140212, armed140211, late1, early0, cancelled0, resync0.
  SOF waits139605, callbacks139605, SOF arms139604. Timer max lateness118us;
  callback max25us. The full120-second microphone session ended with zero late
  enables. The single late count appears in the second native session; its exact
  time was not logged. Audio NAK totals1 then3; latest at204.918s before the
  second PCM bridge trigger204.965s, consistent with startup recovery. This does
  not independently timestamp the late callback or prove no audible effect.
- Thus the strict zero-new-late acceptance criterion was not met, despite
  continuous native audio and no recurring active-window audio failures.
  The additional30-second session added no late counts:170317scheduled,
  170316armed, late still1;139604→169632 SOF arms. Audio disabled events line up
  with host closure. Do not mislabel closure/startup counters as sustained loss.
- Encoder4495/603frames: zero failed/corrupt/invalid/timeouts/resets.
  Source4495/602completed, zero source drops.
- Long-session audio bridge~5.01%CPU. ALSA capture+playback queues
  45.917–69.25ms, median49.188ms; sequential readings, not acoustic latency.

The isolated kernel change removed the predicted interrupt pattern and all
payload loss in that recovery path. This strongly supports premature audio
enabling and shared incomplete-IN recovery as the major remaining corruption
mechanism. Residual NAK misses, the isolated late audio enable and unmeasured
acoustic delay remain separate limits. No new image or production change was
made in this verification turn; no additional flash is justified solely by
these remaining counters.

## Evidence and limits

Host comparison: summary.json, combined.json, post-readback-combined.json.
Target analysis: irq-windows.json, transport-summary.json, thread-costs.json,
reconciliation.json, post-readback-counter-delta.json. Raw logs retained.
Target snapshots are sequential and include diagnostic overhead. Thread and
IRQ runtime accounting overlap; do not sum them as disjoint CPU consumers.
Scene/exposure are not controlled across firmware runs. Suspend/resume and
physical acoustic delay remain untested. No USB serial, physical-drive writes,
card extraction or acoustic playback/chirps. All capture sessions finished.

- target.log SHA256:`d027d60c4bfc571921aaecebcb21199ae334fdb94808fa07d2f2c90e21a8ec35`
- target-usb-counters.log SHA256:`25df9c2481dab8774c613e637ff5a450d21e522ace0dc3b01966cd6c0c797840`
