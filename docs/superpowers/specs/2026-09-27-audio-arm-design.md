# Delayed audio endpoint enable

Goal: reduce the measured ~4000 incomplete-IN events/s during simultaneous
video and microphone use. Acceptance remains smooth simultaneous A/V and low
acoustic delay. This scheduling change alone does not establish acceptance.

Scope: high-speed, buffer-DMA, isochronous IN endpoints with interval8 only.
Prepare DMA/size registers and keep normal ep->req ownership. Delay only EPENA
until approximately target−3 microframes. Schedule once at
now+(modular_distance−3)*125000ns when distance is4..8; otherwise retain the
immediate path. On-time arm gives250–375us margin and approximately one extra
EOPF per millisecond. One timer plus one incomplete replaces four incomplete
interrupts: expected net~2000IRQ/s reduction, contingent on hardware behavior.
Do not claim guaranteed timer latency or30fps.

A prepared request retains DMA ownership but is hardware inactive. Distinguish
prepared ownership from a pending timer. The callback takes hsotg->lock, validates
software power state before MMIO, endpoint activation, epoch/session/target,
request identity, and deadline. Rebuild the control command from live registers.
Write EPENA only for a future target. Early callbacks fall back to immediate
arming once, never reschedule in a loop. Late callbacks preserve prepared state
and permit existing host-NAK recovery; a modular/monotonic expiry guard forces
recovery across wrap. For prepared age>=2ms, SOF discontinuity/wrap can make
elapsed slots ambiguous: reanchor to latest same-phase slot, retire one stale
packet, retain the remaining bounded gadget queue. Count this resynchronization;
it deliberately does not synthesize one PCM callback per unobserved slot. The
ordinary short-delay path retains per-slot consumption. Publish the next target
before giveback so reentrant queueing cannot double-advance it. Completion cancels before DMA unmap/giveback. Stop must
skip hardware waits for never-enabled requests. Core reset, disconnect,
suspend/LPM and power transitions invalidate pending work before clocks change.
Removal drains timers outside the controller lock. Actual-arm diagnostics must
record the eventual hardware write, not preparation.

Alternatives rejected: target−1 leaves inadequate phase/jitter margin;
queue-head-with-reqNULL complicates cancellation and recovery; reducing video
polling alone introduces same-parity incomplete events; skipping many audio
callbacks changes PCM consumption semantics. Do not bundle GPIO, encoder,
USB descriptors, ALSA buffering or diagnostic-control changes.

Tests use actual extracted driver functions with synthetic MMIO/time. Cover
normal and near-target starts, wrap, no-SOF/early fallback, late callback and
NAK, cancellation, callback requeue, reset/suspend, endpoint disable and memory
lifetime. A model can verify software decisions, not physical timer deadlines.
ARM build and patch application must match reviewed sources. Hardware logging
must expose scheduling, arming, late/fallback/cancel counts and callback lateness.

Existing authorization covers reversible implementation/build/testing. No
physical-drive write, serial, commit or push. Keep the last tested image intact.
