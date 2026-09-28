# Targeted interrupt diagnostics

This is instrumentation, not an A/V fix. Patch0007 preserves the transfer
selection and recovery policy of the flashed coalesced-fix kernel. It adds
bounded measurements to the existing `isoc_stats` file, which patch0016 can
retrieve over the existing UVC extension unit. No additional USB endpoint,
interface, console, or networking is introduced.

## Why these measurements

The existing logs show damaged video, missed payloads, and about 12,800 USB
interrupts/s with audio active. They omit global interrupt causes, handler
duration, and the state when the driver decides to disable an endpoint.
Merely retrieving those same logs through USB cannot fill that gap.

The native replay demonstrates an ambiguity: a previous-frame incomplete-IN
event serviced in the current frame can select the same pending video request
as a genuine current-frame miss. It does not establish that the former event
sequence occurred on the Pi. The tempting comparison-only change to defer
recovery was **rejected offline**: both interval-1 and interval-8 cases fail
at frame-counter wrap, even assuming the next host poll causes NAK recovery.
See `replay-dwc2-incomplete.py`, `incomplete-replay-results.txt`,
`reject-strict-past-recovery.py`, and `strict-past-rejection.txt`.

## Recorded evidence and interpretation

- `irq_causes`: status-pass count, masked incomplete-IN observations,
  observations before the current frame's EOPF threshold, and endpoint-disable
  selection counts. `probe_ns` measures only the timestamp/DSTS-read bracket;
  it is **not total instrumentation overhead**.
- `irq_work`: gadget-handler entries, passes with masked IN/OUT endpoint
  interrupts, incomplete-IN passes without either endpoint-interrupt bit,
  cumulative gadget-handler time and maximum duration. Other global causes
  can coexist with `incomplete_only`. Handler time includes callbacks,
  retries, recovery and these diagnostics, but excludes the preceding common
  handler and small entry/exit portions. It is not total USB IRQ CPU time.
- `irq_endpoint`: per-IN-endpoint observations where the endpoint is active
  with a future software target, selected for disable, or has NAK/completion
  status. Completion bits can be suppressed by existing coalesced recovery;
  this is not a successful-request counter.
- `irq_coverage`: adjacent-frame observations and current-target selections
  eligible for the timing bound. A zero early-selection count with little
  eligible coverage cannot exclude the suspected sequence.
- `irq_decision`: first eight selections and first eight early current-target
  selections, with timestamps, cached/live/target frame numbers, endpoint
  control/status/remaining transfer size, DCFG, session, request-arm serial,
  payload length, and frame reads bracketing the endpoint-enable write.

Counters describe observed register bits and can overlap or repeat within an
IRQ entry. They must not be added as independent hardware event counts.
Snapshots are fixed-size and read-only; formatting/allocation happen only in
debugfs read context. No per-interrupt printing occurs.

## The timing bound

The previous timestamp precedes a live frame-register read reporting F.
The current timestamp follows a live read reporting F+1. Therefore the elapsed
time between timestamps bounds the age of F+1 from above. If it is below the
configured EOPF offset, with a 10 us margin, an already-pending incomplete-IN
event was observed before this frame could generate that event at EOPF.

This depends on the controller's live-frame and EOPF semantics and an
uninterrupted bus epoch. Classification requires high-speed buffer DMA and
rejects reset, suspend, fault, speed, and relevant lifecycle transitions.
The disable-selection sample repeats live state/time checks so callback delay
cannot silently turn an early entry observation into an early decision claim.
The independent review found this ordering conservative under those assumptions.

An early selection does **not** by itself establish audio origin, physical
disable before the host token, or preventable loss. Arm reads do not prove
FIFO readiness or precise subframe enable timing. A current request may
already have failed a token even before EOPF. The diagnostics themselves add
work; results describe the instrumented run.

## Offline validation

Against the prepared actual kernel source:

- Real predicate: 458,752 assertions covering all 16,384 frame numbers,
  four EOPF settings, strict cutoff, counter wrap, invalid epochs, clock
  reversal, nonadjacent frames and long gaps; warnings-as-errors and UBSan.
- Real sampling functions: 11 synthetic MMIO/clock scenarios, including
  callback delay, frame transition, pending reset/fault, suspend, speed change,
  request metadata, bounded storage and frame wrap; warnings-as-errors and UBSan.
- Existing real recovery-function replay: 19 cases still pass. Its fake
  controller structure was extended only to accommodate diagnostic counters.
- Independent review of the implementation found no remaining blocking issue.

Commands (`SRC` denotes the patched kernel's `drivers/usb/dwc2` directory):

```
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I"$SRC" diagnostics/check-irq-age.c -o /tmp/pisight-check-irq-age
/tmp/pisight-check-irq-age
python3 diagnostics/check-irq-sampling.py "$SRC"
python3 diagnostics/check-dwc2-coalesced.py "$SRC/gadget.c"
```

No hardware performance or diagnostic readback success is claimed by these
offline checks. The previous USB-readback-only image remains held.

## Verified candidate

`diagnostics/sdcard-irq-cause-diagnostics.img`, 41,398,784 bytes.
SHA256: `a2d2ba2032750a79338960732bf45b38c464fc2e33b8fb5d55af970845f36b0b`.

Final ARM kernel/image build exited 0. Compared with the held USB-readback
image, rootfs file contents/modes/symlinks are identical and the only changed
boot file is `zImage`. Packaged kernel/rootfs bytes match exported build
artifacts, whose hashes match the Linux build. All five compiled diagnostic
source files match the reviewed/tested source. See
`irq-cause-image-verification.txt` and `irq-cause-source-SHA256SUMS`.

The first compile caught use of Linux's reserved `current` macro as a
parameter name. Renamed to `current_frame`, added a native macro-collision
check and rebuilt. Final build has no compiler warning/error for this change;
the existing four Buildroot `comm` inventory notices remain nonfatal.

After the user flashes and connects this candidate, run the existing automated
capture. It attempts USB log/counter retrieval after measurements. Then use
`python3 diagnostics/summarize-irq-causes.py PATH_TO_LOG` on the retrieved data.
The reader refuses older logs that lack these counters rather than treating
missing evidence as a negative result. Readback still needs hardware validation.
No physical drive was written, and no commit or push was made.
