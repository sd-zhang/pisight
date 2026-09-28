# DWC2 coalesced completion/disable correction

Card readback: `target-transport-diagnostics.log`, SHA256
`59a3d620e6f8bab2c6075b61a85dbdcfed6662354d9825c946d08cf075dff834`.
The new diagnostic markers, DMA mode and endpoint parameters are present.

## Hardware evidence

Video ep1in, buffer DMA, interval1 (125us): 1,316 disabled-handler misses
(714 payload), 23 NAK-handler misses (5 payload), zero start/out-token misses.
All 719 payload and 620 empty misses reconcile exactly with the two UVC stream
summaries. No large wrap burst occurred in this run (disabled max2, NAK max4).

The first disabled recovery snapshot records:

```
ns=145166469000 cached=2361 live=2361 target=2362 overrun=0 last_irq=0x3
```

That is a request discarded before its target frame, with completion and
disabled interrupt bits asserted together. The source dispatches completion
first: it advances the target, retires the old request, and may start the next.
Disabled recovery then flushes the FIFO and unconditionally retires the queue
head. This explains the recorded invalid state. Request identity and DIEPTSIZ
at IRQ entry were not logged; source/replay reproduces a preceding sequence consistent with the snapshot,
rather than directly recorded hardware request IDs.

Only the first sampled event proves premature retirement. The other 1,315
disabled misses cannot all be attributed to the same defect from these samples.
The host trial remains a failure: 26.18fps mic closed, 19.42fps mic active,
26.29fps closed again, with 462 JPEG errors in the stable microphone window.
Encoder reports no timeout/error/corrupt/source-drop events.

## Correction

Kernel patch0006 extends the existing NAK exclusion to EPDISBLD for normal
isochronous IN completion. Disabled recovery owns the original request once;
completion cannot start the next request before that FIFO flush. This applies
to buffer DMA and slave mode; DDMA, non-isoc and OUT dispatch are unchanged.
It conservatively reports ENODATA for the old transfer even if it reached the
host. No USB descriptors, audio buffering, clock, encoder or timing-trial
changes are bundled.

`check-dwc2-coalesced.py` extracts the real IRQ prefix (through NAK), completion,
queue retirement/start-next, recovery and frame arithmetic functions. Fake
MMIO, DMA setup, locks and callbacks allow native deterministic replay. Queue
refill models an existing multi-request queue, not production ep_queue's
immediate-start behavior when requeuing into an empty queue. The single-request
case does not refill. This is not a USB controller emulator or performance test.

Original code fails9/19 cases; corrected code passes19/19 with UBSan. Coverage
includes recorded ordering, multi-request callback refill, single request,
empty payload, interval8, wrap, normal/NAK/disabled combinations, slave mode,
bulk/EP0/OUT/DDMA dispatch and subsequent NAK plus successful completion.
The wrap replay exposes16,385 callbacks instead of one with the original code;
that is an injected boundary reproduction, not a wrap storm observed this run.
AddressSanitizer startup did not reach main in this Mac sandbox; no ASan claim.

Independent review found no blocking defect in this narrow correction and
requested the sequential NAK case, honest callback scope, production initial
frame sentinel and slave-mode coverage; all are included.

A later NAK can still legitimately discard an expired request before resuming.
Therefore corrected ownership/order does not itself demonstrate fewer dropped
host frames. Candidate performance and the full simultaneous A/V requirement
remain unverified until hardware capture. The old1024/250us trial stays held.

## Microphone evidence

`target-transport-summary.json` is reproduced by
`summarize-target-transport.py`. Its28 periodic active snapshots show combined
capture/playback ALSA delay42.96–50.04ms (median49.09ms), at1GHz CPU frequency.
Alsaloop consumed about3.14% CPU across116.38s of the first session and3.46%
across15.30s of the second (ARM USER_HZ100). The four audio recovery misses
coincide with the two opens and closes; no active audio misses were sampled.
These are sequential ALSA readings, not acoustic end-to-end latency; userspace
and host queues are excluded. They do not explain the user's much larger delay.

## Verified candidate artifact

`diagnostics/sdcard-coalesced-usb-fix.img`, 41,394,688 bytes, SHA256
`c969e4fffa84b50388fb617d2a7aa975e740aad3107ea602b7b8754e84f79d69`.
Kernel SHA2561604f95b2539afb92ad6382a07b0e488cebc589e9789a37440b3fb7506b1bee2.
Build exited0; tar-stream export hashes match the Linux originals. Packaged
kernel/root partitions verified. Rootfs file inventory unchanged; FAT file
inventory changes only ZIMAGE. Source gadget.c SHA256
70c69790e63cee780638f14c6596c8bc5f04073cda0f89438baa267b2f330c59 matches the
replay source and Linux build source. isoc_stats_show remains in vmlinux.
Diagnostic helper tests pass. Build log has no compiler warnings/errors; four
nonfatal `comm` notices concern missing Buildroot before-install inventory files.

Build log: `build-coalesced-fix.log`. Verifier: `verify-coalesced-image.py`;
results: `coalesced-image-verification.txt`. Local extraction/source staging:
`/private/tmp/pisight-coalesced-fix/`. Docker volume source/output now includes
patch0006. No card writes, commits or pushes performed. Hardware performance
of this candidate is untested.
