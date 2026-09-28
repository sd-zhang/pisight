# Guard recovery from an old incomplete-IN event

Success still means smooth simultaneous camera video and low-delay microphone.
This correction addresses a measured driver error; it is not yet a demonstrated
solution to the complete A/V problem.

The hardware evidence and its limits are in
`capture-irq-cause-20260927/results.md`. In particular, a 2,048-byte video request
armed in microframe 12912 was disabled and retired in 12913 before that frame's
EOPF. A global event from an earlier frame was being attributed to it. The
controller's global cause does not identify which endpoint generated it.

## Correction

Kernel patch0008 follows patch0007 and uses its frame/time and request-arm
observations. These observations now participate in correctness and cannot
be removed independently as optional logging.

1. Acknowledge the old incomplete cause first, then read the register back.
   Observe live frame/time after that ordered acknowledgement. No final W1C
   occurs after scanning endpoints, so a later EOPF stays pending.
2. Defer only a current-target active request when both the post-ACK and
   decision-time observations satisfy the conservative pre-EOPF bound in a
   valid high-speed buffer-DMA bus epoch. Other requests retain normal recovery.
3. Store arm serial, endpoint session, target, bus epoch and timestamp. Normal
   completion/rearm/cancellation/session changes cannot pass ownership to a
   reused request. A genuine later EOPF uses normal recovery.
4. An identical deferred request serviced after frame-counter wrap can be
   recovered using modular age. An elapsed-time bound resolves long-delay
   ambiguity. The 250 us check runs when another incomplete event is serviced;
   it does **not** introduce a timer or promise recovery within 250 us.
5. Reset/suspend/speed/mode/ID/controller-error observations invalidate the
   epoch. Identity is rechecked after decision sampling before authorizing
   forced recovery across wrap.

This differs from the rejected strict-past comparison: it excludes an event
proved to predate the request's EOPF and preserves that deadline's later event.
It does not assume that the next IN token will generate a NAK interrupt.

New `irq_recovery` counters report deferral decisions, successful completions
of still-identical deferred requests, and selections for deferred recovery.
Recovery selection is not confirmed retirement. Existing `selected`/decision
diagnostics now include candidates which the guard leaves enabled. Compare
actual missed-payload counters and host decode results to establish benefit.

## Verification

`check-incomplete-defer.py` extracts the actual production functions and runs
clock/MMIO fixtures, including the captured early selection. Final baseline
fails 4 of 26 cases; corrected source passes 26/26. Coverage includes ordered
acknowledgement, events before/during/after W1C, later events during endpoint
scan, conservative fallback, genuine later recovery, counter wrap, long delay,
request/session/epoch changes and a transition during decision sampling.

Independent review reproduced a decision-time reset race in the first version.
Four added transition cases failed before the correction and pass afterward.
The reviewer independently reran the final 26 cases and found no remaining
blocking issue in the reviewed scope.

Actual request/queue recovery replay passes 22/22, including successful
completion accounting after target advancement, failed retirement, old-session
ownership and the previous coalesced-interrupt regressions. Diagnostic sampling
passes 11/11; the timing predicate passes 458,752 assertions. Native tests use
warnings-as-errors where supported and undefined-behavior sanitization. These
fixtures are not a USB bus emulator and do not establish hardware throughput.

Source is staged in `/private/tmp/pisight-incomplete-defer/{base,new}`. Patch
application to the actual flashed baseline matches all five staged source
files exactly. `incomplete-defer-source-SHA256SUMS` identifies those files.

The ARM kernel/image build exited 0 with no compiler errors or warnings for
the change. Four existing Buildroot inventory `comm` notices remain nonfatal.
Kernel checkpatch (local patch, `--no-signoff`) reports zero errors and four
block-comment-format warnings; this style check exits 1 and is not claimed
clean. No personal DCO sign-off was invented for an upstream submission.

Verified image: `sdcard-incomplete-event-fix.img`, 41,398,784 bytes, SHA256
`c03c1a3c25a78d6caba028e2336da4e97604a3e8f8d8ae447f7b5a097a26c45e`.
Compiled source hashes equal reviewed/tested source. Packaged kernel/rootfs
match Linux-exported artifacts. Compared with the flashed IRQ diagnostic
image, rootfs file contents/modes/symlinks are identical and only boot `zImage`
changes. See `incomplete-defer-image-verification.txt`. Hardware untested.

## Remaining limits and acceptance

Approximately 4,000 extra incomplete observations/s while audio waits remain.
This correction adds bounded register/time reads to that path. It does not
establish that every spared video request can still reach the host, and it
does not measure or change acoustic microphone delay. CPU pressure and source
frame rate may remain limiting after malformed JPEGs are reduced.

Hardware validation must repeat sustained simultaneous capture, checking
distinct video frames and damaged JPEGs, microphone continuity and acoustic
delay, plus start/stop/reopen recovery. Solo video is a comparison, not success.
Keep full XU log retrieval after performance measurement; the user previously
saw persistent degradation with USB serial. XU readback on the preceding build
worked, and a post-readback check recovered normal solo-video throughput.

The user alone flashes any physical drive. No commits or pushes are authorized.
