# Coalesced-fix card readback — 2026-09-27

Read-only copy: `target-coalesced-fix.log`.
SHA25661ae7f5d2102049e81a0cf1db5a08eeb1e3309c75b27016387d8f3bda9387199
matches mounted PISIGHT.TXT. Mounted zImage SHA256
1604f95b2539afb92ad6382a07b0e488cebc589e9789a37440b3fb7506b1bee2 matches
candidate kernel exactly. Thus the reported flash contains the intended kernel.

| Video recovery | Before | After |
| --- | ---: | ---: |
| Disabled total misses |1316|1255|
| Disabled payload misses |714|676|
| Disabled maximum burst |2|1|
| NAK total misses |23|614|
| NAK payload misses |5|6|
| All payload misses |719|682|
| All empty misses |620|1187|

Both logs' endpoint counts reconcile exactly with UVC stream summary totals.
The after run's two UVC sessions report599/83 payload misses and1061/126 empty
misses. Disabled first/worst sample: live=target6015, IRQ0x2002. An intermediate
last sample with IRQ0x3 has live=target5109, consistent with corrected request
ownership. None of the recorded after samples has the previous future target.
First/latest/worst samples are not a trace of every recovery; they cannot prove
that no other premature retirement occurred. The NAK increase is almost all
empty requests, consistent with recovery waiting for resynchronization as
predicted by the offline sequential replay.

Host simultaneous performance did not improve: stable mic-on19.487fps/457 JPEG
errors versus19.422fps/462 previously. Do not characterize the payload count
change as statistically demonstrated performance improvement.

Full active window68.61–133.37s:94.18% CPU busy and12810 USB IRQ/s. Previous
full active193.99–258.61s:94.01% busy and12792 IRQ/s. These aggregate measurements
support timing pressure but do not identify IRQ service latency or a specific
operation blocking the125us video interval. CPU accounting is not a trace;
thread ticks must not be presented as exclusive causal attribution.

Encoder first session3596frames, mean13253us/max18906us; source3595/dropped0.
Second436frames, mean13448us/max17470us; source436/dropped0. No reported failed,
corrupt, invalid, timeout or reset events. Flags/markers are not full JPEG decode.

28 active periodic microphone snapshots: combined ALSA delay45.25–69.92ms,
median49.72ms; bridge3.19%/2.81% CPU in two sessions. Audio endpoint has two NAK
misses at opens and two disabled misses at closes. No measured acoustic delay;
sequential ALSA reads exclude userspace and host queues.

Reproduce analysis with:

```
python3 diagnostics/compare-target-usb.py
python3 diagnostics/summarize-target-transport.py diagnostics/target-coalesced-fix.log --output diagnostics/target-coalesced-summary.json
```

The exact initiating video-transfer fault remains unproven. More patches to
recovery ordering are not an evidence-supported performance remedy. The current
USB arrangement requires software scheduling every125us. The controller's
buffer-DMA frame tracking limitations are described in the original upstream
change already present in this kernel:
https://lkml.iu.edu/2109.3/02936.html
The old1024/250us trial remains held, not silently added to the next artifact.

A diagnostic readback addition is being prepared to remove card extraction from
future log collection: selector2 on the existing PiSightSettings1 UVC extension
unit, fixed60-byte responses, immutable bounded snapshots of the existing log
or live recovery counters. No added USB interface/endpoint or file writes.
This does not fix A/V performance and requires new firmware before it can work.
