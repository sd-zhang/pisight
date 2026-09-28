# Delayed audio enable candidate

Patch0009 has now been tested on hardware. It reduces incomplete interrupts
from3987/s to997/s and video payload failures from322 to93. Mic-on distinct FPS
is20.594 with74 JPEGerrors; totalCPU remains94.89%. Smooth A/V is still unsolved.
See [captured results](capture-audio-arm-20260927/results.md).

Patch0009 changes only kernel scheduling of high-speed buffer-DMA IN endpoints
with interval8. DMA/queue ownership is retained while EPENA waits until about
three microframes before target. Measured140190timers had1latecallback and no
resync; active callback elapsed fraction~0.60%. Fewer interrupt events did not
produce a measured decrease in overall CPU or gadget-handler time.

## Ownership and fallback

Video interval1, DDMA, full-speed and runtime low-resolution timer paths retain
immediate enabling. The timer validates active controller power, endpoint,
request/session/epoch, target frame and pending endpoint recovery before writing
EPENA. It records the actual write in existing arm diagnostics.

Late callbacks leave prepared ownership for NAK recovery instead of enabling a
stale packet. A modulo-safe predicate handles the frame counter crossing zero.
For prepared age>=2ms, the elapsed SOF count is ambiguous: resynchronize to the
latest same-phase slot, retire one stale packet and retain the remaining bounded
audio queue. Count this as resync; do not equate it with per-missed-slot PCM
catch-up. Publish the next target before giveback, then recheck session/epoch and
power state before further MMIO. Cancellation precedes DMA unmap and callbacks.
A never-enabled request skips hardware-disable waits. Power/reset paths invalidate
timers before clocks change; removal drains callbacks outside the controller lock.

The Linux timer API distinguishes nonblocking cancellation from cancellation
that waits for an executing callback. The implementation uses those in locked
invalidation and final removal respectively. [Kernel API documentation](https://www.kernel.org/doc/html/v6.2/driver-api/basics.html).

## Native evidence

- 32 scheduling/timer checks pass. Original source fails3/4 initial tests because
 it enables immediately and reports preparation as an actual arm.
- 97 actual-source request/recovery cases pass, including 64 resync wrap phases.
 Baseline failures: 4 lifecycle,2 long-absence,28 wrap-phase and3 giveback epoch/power.
- 26 incomplete-event and 11 sampling cases still pass.
- 458752 timing-predicate assertions pass.
- Independent review found runtime-hres, resync-wrap and giveback power/epoch
 issues; each was reproduced and corrected. Final review reports no source blocker.
- Patch application reproduces all five reviewed driver files exactly.

Harnesses supply MMIO and clock inputs. They cannot establish physical host-token
behavior, timer latency or sustained A/V performance. Existing queue tests model
the external giveback callback; the scheduling harness executes actual start_req
and timer functions. Counter-wrap is exhaustively sampled over all 8×8 resync phases.

## Hardware acceptance

After the user flashes/reconnects, verify `irq_arm_policy interval=8 lead=3` via
existing UVC readback, then run the standard concurrent capture. Compare unique
FPS, decoder errors, UVC payload misses, audio continuity and queue delay.
Retrieve target logs AFTER measurement. Inspect `arm scheduled/armed/late/early/
cancelled/resync`, max lateness and callback duration. Gadget IRQ time excludes
new timer work; compare total CPU and IRQ rates too. Callback duration includes
lock wait and is not exact CPU attribution. Measure acoustic latency separately.

No USB serial, added USB interface, physical-drive write, commit or push.
The previous tested image remains available. This candidate changes neither
ALSA buffering nor video formats, encoder, GPIO service or diagnostic controls.
