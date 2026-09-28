# Simultaneous A/V remains failing — 2026-09-27

Goal: smooth camera video and low-delay microphone **at the same time**.
Video-only recovery and successful log retrieval are diagnostic checks, not
acceptance of the webcam's behavior. Acoustic microphone delay is not yet measured.

The user connected the IRQ diagnostic firmware. One preflight counter read
confirmed patch0007 before capture; this was not a never-accessed-diagnostics
baseline. A 150-second video session opened the microphone for 120 seconds,
followed by 20 seconds of native simultaneous A/V. Full USB log retrieval was
after those captures and the diagnostic save window, using the existing UVC
extension unit. Both log and counter retrieval succeeded without card removal.

| Stable window | Distinct video fps | JPEG decode errors |
| --- | ---: | ---: |
| Before microphone | 23.314 | 0 |
| Microphone active | 18.307 | 432 |
| After microphone | 25.302 | 0 |

Mic-on maximum changed-frame gap: 557.137 ms. The separate native combined run
delivered 320 distinct frames out of 594 callbacks (16.117 distinct fps), with
274 repeats. Its audio delivered 960,512 samples / 20.0107 seconds at 48 kHz,
with no timestamp gaps greater than 1 ms. This establishes sample continuity,
not acoustic latency. The FFmpeg recording's missing sample-seconds must not
be attributed to target audio loss: that AVFoundation capture path overwrites
an unconsumed audio frame.

After full log retrieval, a 30-second video-only check delivered 711 distinct
frames, no repeated hashes, and 23.845 distinct fps. Thus this run did not
reproduce the persistent ~18 fps state the user previously observed after
opening USB serial. It does not prove the new instrumentation/readback is free
of timing effects, nor establish exact before/after equivalence across scenes.

## Target transport and encoder

The two UVC summaries report 538 + 152 = **690 failed payload transfers** and
16 + 7 = 23 failed empty transfers, with zero other errors. These reconcile
exactly with ep1 disabled (679 total / 677 payload) and NAK (34 / 13) counters.

Encoder session one: 3,311 frames, mean 13,333 us / max 18,557 us.
Session two: 440 frames, mean 13,345 us / max 19,106 us. No reported failed,
corrupt, invalid, timeout, or reset events; source dropped=0 in both sessions.
These encoder status counters are not a full independent JPEG decode.

Active ALSA combined queues: 42.333–71.125 ms, median 49.542 ms across 28
periodic snapshots. Bridge CPU: 3.63% and 3.92% in the two sessions. These
sequential queue readings exclude userspace/host queues and acoustic delay.

## New causal evidence

560,410 global incomplete-IN observations, 544,486 without endpoint interrupt
bits; audio was waiting for a future software target in 560,407 observations.
There were 140,198 audio completion-bit observations: approximately four
incomplete interrupts per audio completion. This fits immediate rearming of
the interval-eight audio endpoint with unchanged parity; it is not a hardware
per-endpoint attribution of the global interrupt.

There were 906 endpoint-disable selections (904 video / 2 audio), of which
462 selected a current-target request before its current-frame EOPF bound.
The first eight early samples are odd video targets, armed in the preceding
even microframe, with 2,048-byte payloads. All have both arm frame reads in
that preceding microframe. Selection count is not retirement count.

The first sample can be matched to actual failed-request retirement:

- Previous live frame 12912 read after timestamp 80,632,345,000 ns.
- Disable decision at 80,632,397,000 ns: live=target=12913.
- Failed retirement at 80,632,415,000 ns: live=target=12913.

Under the documented adjacent-frame/EOPF assumptions, current-frame age is at
most 52 us at selection and 70 us at retirement, before configured EOPF at
100 us. The earlier event therefore selects and retires a request before that
request's own EOPF deadline. This is stronger than the earlier hypothetical
replay. It still does not prove the host had not already issued its video
token, or that every damaged frame is preventable by deferring recovery.
Raw DIEPINT bit 4 is sticky and unmasked in this path; do not attribute it to
the sampled request. FIFO/packet counter interpretation needs separate care.

During the mostly active snapshot window, incomplete observations were about
3,847/s, gadget IRQ entries 12,467/s, handler time 11.94% of elapsed time, and
aggregate CPU busy 94.50%. Snapshot headings precede slow shell collection,
so rates are approximate. Handler time includes instrumentation and callbacks
but excludes the separate common IRQ handler; it is not total USB CPU time.

## Next correction under review

A narrowly guarded deferral could preserve current-target requests when the
old global event is provably pre-EOPF. It must acknowledge the old event before
proving the timing bound, avoid clearing a later event at handler exit, and
provide recovery across frame-counter wrap without assuming a subsequent NAK.
No performance-fix image has been built from this proposal. The prior naive
strict-past policy remains rejected. Full A/V success remains unproven.

Raw target log SHA256:
`6540c35bd982f94746bcf5af6d654156c6b3582f9d3cdecc47b9f8eba86adf52`.
Live counters SHA256:
`4559f0f0c4a721704a5bd48b8aad46fbfe81694a6f53fb8857513178def1bca8`.
See `summary.json`, `irq-analysis.json`, `irq-windows.json`,
`transport-summary.json`, and `post-readback-video.json` beside this report.
