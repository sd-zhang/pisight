# Patch0008 hardware result: partial improvement; simultaneous A/V still fails

The connected device exposes the new `irq_recovery` counters. This establishes
patch0008 functionality is running, not an independently read kernel hash.
Candidate image: `../sdcard-incomplete-event-fix.img`, SHA256
`c03c1a3c25a78d6caba028e2336da4e97604a3e8f8d8ae447f7b5a097a26c45e`.

## Host capture

The existing script ran 150 seconds of 720p video, with microphone enabled for
120 seconds, followed by 20 seconds of native combined capture. Saved target
logs were retrieved through the existing UVC extension after measurements.

| Stable window | Distinct fps | JPEG errors | Longest distinct-image gap |
| --- | ---: | ---: | ---: |
| Before microphone | 25.759 | 0 | 70.720 ms |
| During microphone | 19.807 | 220 | 394.439 ms |
| After microphone | 26.086 | 0 | 95.419 ms |

The pre-mic stable window is only 5.968 seconds owing to capture startup.
Native combined capture delivered 17.724 distinct fps (353 distinct images,
245 repeats); audio contained 960512 samples over 20.0107 seconds with no
sample timestamp gaps over 1 ms. Acoustic microphone delay is unmeasured.
FFmpeg audio sample shortage is not evidence of target audio loss: its
AVFoundation input can overwrite unconsumed audio buffers.

A separate 30-second combined capture AFTER log readback delivered 18.977
unique fps (563 distinct, 331 repeats), 1440768 audio samples, zero timestamp
gaps. This does not show an additional persistent slowdown from readback.
Scene differences prevent a precise performance comparison. Main target logs
do not include this later capture; do not mix its counts with main totals.

## Target evidence

All 334 guarded requests completed successfully: deferred=334, completed=334,
recovered=0. This is hardware evidence that the old-event guard prevents real
loss. It does not prove all remaining premature retirements are eliminated.

Video payload misses fell from the previous run's 690 to 322: disabled 290,
NAK 32. Another 70 empty requests were missed. Payload/empty totals reconcile
exactly with UVC session summaries (272/54 and 50/16). There were zero encoder
failures, corrupt frames, invalid buffers, timeouts or resets. Encoded source
frames: 3362 and 409; mean encode durations approximately 13.32 and 13.45 ms.
Different scene/exposure and window timings limit between-image comparisons.

During the full active snapshot interval 130.16–195.53 target seconds:
12661 gadget IRQ entries/s, 3987 incomplete observations/s, 3880 incomplete-only
observations/s, 12.95% gadget handler time, 94.81% aggregate CPU busy. Video and
audio endpoint completions were approximately 7978/s and 997/s respectively.
Snapshot collection is not atomic, and instrumentation contributes overhead.

Audio's 232-request NAK recovery burst occurred at target 275.036193 seconds,
after video STREAMOFF at 274.740329 and immediately before mic shutdown. There
were no audio NAK/disabled misses in the full active snapshot interval. Do not
report the shutdown burst as sustained-stream loss. Active ALSA queues were
45.604–50.5 ms, median 49.823 ms; this is not end-to-end acoustic latency.

## Raw evidence

- `summary.json`: host windows and native captures.
- `post-readback-combined.json`: later combined check.
- `reconciliation.json`: exact target/UVC accounting.
- `irq-windows.json`: cumulative snapshots and approximate rates.
- `irq-analysis.json`: saved-snapshot analysis, not final live readback totals.
- `target.log`: SHA256 `1ebdd0702dc0e1e6f8ba34f29180972ec79c0e590a1a99a9b7950ca78036f3ac`.
- `target-usb-counters.log`: SHA256 `0b3ba16213d9ed502166d3f0494e94550f373f9ae02278f30c4fe710f59ba622`.

## Next work

Smooth simultaneous video and low-delay audio remain the acceptance criteria.
Investigate reducing incomplete interrupts at their scheduling source. A naive
one-microframe timer has inadequate worst-case margin; lowering video's polling
rate can introduce additional same-parity incomplete events. No new scheduling
patch or image has been produced. No serial, physical-drive writes, commits
or pushes were performed. The user handles flashing.
