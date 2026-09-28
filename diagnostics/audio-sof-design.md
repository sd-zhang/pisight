# Frame-aligned audio enable candidate

**Hardware tested:** the recurring incomplete-interrupt pattern and disabled
video payload losses disappeared; mic-on~29.96fps with5 JPEG errors versus69.
Native audio continuous, but one late enable remains. See
[captured results](capture-audio-sof-20260927/results.md); historical unverified
wording below describes the candidate before that test.

The tested LED-events image restores CPU headroom and ~29.4 fps simultaneous
capture, but retains 89 failed video payloads (80 disabled, 9 NAK). All 16 saved
video recovery selections have target modulo8=7; the audio polling phase is0.
Source/clock evidence supports an incomplete interrupt from the prematurely
enabled audio endpoint in target−2 being handled during video target−1.
The bounded samples do not prove attribution of every failure.

A simple timer lead3→1 leaves only0–125us before target because preparation
phase is inherited. Observed102us timer lateness and23us callback max cannot
establish safety. Do not promote that constant-only candidate.

Instead wake the timer in target−2. If already in target−1, validate and arm.
If earlier, enable SOF interrupt temporarily, keep DMA ownership, and arm only
when live DSTS is target−1. ACK SOF before inspecting frame/state; handle it
before endpoint completion work. Mask SOF when no endpoint awaits it. Do not
arm early on stalled SOF; age>=2ms and target/past checks retain NAK recovery.
Distance2 preparation must use this gate as well. Retain immediate interval1,
DDMA, full-speed and runtime low-resolution fallbacks. Existing conservative
incomplete guard and PCM retirement remain unchanged.

Validate request/session/epoch/power twice around MMIO as before. Cancellation
clears SOF waiting before DMA giveback and masks only with accessible registers;
never touch powered-off MMIO. Shared mask remains enabled for another waiter.
A stale SOF bit cannot imply a frame transition. Reset coalescing must never
resurrect an endpoint. Same-frame/past callbacks leave NAK recovery ownership.

Nominal timer+oneSOF replaces timer+oneincomplete; CPU improvement unclaimed.
SOF interrupt delay can still miss audio; target validation prevents stale
arming, not missed deadlines. Hardware acceptance requires continuous audio,
no new late/NAK losses, sustained unique FPS, lower JPEG/payload failures and
lower incomplete count; measure total CPU. Acoustic delay remains unmeasured.
Build an isolated kernel-only image using exact tested LED-events rootfs,
without the untested shutter change. User alone flashes; no serial/drive writes.

## Verification and candidate

Built `sdcard-audio-sof.img`:41419264bytes, SHA256
`4e24ecde63ef34d3844cfee556c1c0c2906a68ccde075f13e81c7a087394f89a`.
Kernel patch0011 is under `webcampi/board/raspberrypizero/linux-patches/`.
Existing interval1 video format/endpoint scheduling, microphone name, CPU fixes
and diagnostics stay in the exact tested LED rootfs. The separate, untested
shutter switch is intentionally absent from this isolated candidate.

- Actual scheduling-function replay:397127 checks pass natively with UBSan and
  under ARM1176 QEMU. Original source fails25of63 initial checks. Exhaustive
  frame positions plus125 preparation phases×361 callback delays cover modeled
  phase/wrap behavior; QEMU executes the functions, not a Pi USB bus.
- Actual queue/recovery replay:101 cases pass including new SOF ownership,
  dequeue, shutdown and wrap retirement. Missing NAK waiting guard reproduced
  with1failure, then corrected. Existing26 incomplete,11 sampling and458752
  conservative age checks pass.
- Independent review reran scheduling/recovery suites and found no blocker.
  Deferred minor: no end-to-end suspend/resume mask-invariant test. The normal
  suspend/LPM/clockgate/hibernate/disconnect callers cancel before power changes;
  reset rebuilds the mask. Calling cancellation only after power is inaccessible
  cannot clear hardware SOF; do not change this lifecycle ordering casually.
- Full ARM kernel rebuild completed successfully. No compiler warnings/errors;
  four existing Buildroot `comm` bookkeeping notices remain in the build log.
- All five compiled DWC2 source hashes match clean patch application. Built-in
  DWC2, kernel release6.12.20. Compiled policy string:
  `irq_arm_policy interval=8 lead=1 timer_lead=2 sof=1`.
- Image exported through tar stream. All component SHA256s match Linux output;
  embedded boot/root partitions match their components; rootfs is byte-identical
  to the tested LED image and ZIMAGE is the only changed FAT file.

Frame validation and the eventual EPENA register write are separate operations;
SOF can cross between them. The design improves the usual timing margin; it does
not guarantee hard deadlines or prove zero audio drops. Source tests cannot
establish actual IRQ latency, CPU use or physical acoustic delay.

Evidence: `audio-sof-phase-evidence.json`, `audio-sof-*-tests.txt`,
`audio-sof-baseline.txt`, `audio-sof-nak-baseline.txt`, `build-audio-sof.log`,
`package-audio-sof.log`, `audio-sof-compiled-source.txt`,
`audio-sof-image-verification.txt`. Reproduce image checks with
`python3 diagnostics/verify-audio-sof-image.py` while exported components remain
under `/private/tmp/pisight-audio-sof/export`.

Packaging uses newly built zImage with a copy of the LED image's boot.vfat:
Linux mcopy replaces onlyZIMAGE, then genimage embeds that FAT and original
SquashFS. This avoids the untested patch0020 already present in Docker's gadget
build tree. Future normal full builds include both0011 and0020; do not confuse
those with this isolated candidate. Docker kernel now includes0011; do not
apply it twice. No physical drive was written. Actual Pi still runs LED image.

## Hardware acceptance after user flash

Run the existing concurrent mic-toggle and native combined capture, then XU
readback. Check the policy string above. Compare the tested baseline's
29.392fps mic-on,69 JPEG errors,89 payload misses,~1000 incompleteIRQ/s and
69.55%activeCPU. Require audio continuity and no increase in late/NAK payload
losses; inspect `sof_waits/sof_callbacks/sof_armed` alongside all prior timer
and recovery counters. Fewer video errors at the expense of audio is a failure.
No new USB interface or serial access is needed. Acoustic latency is a separate
unmeasured requirement.

## Primary reference cross-check

The related Synopsys-style controller in ST RM0033 describes peripheral SOF
interrupts on received SOF tokens and a frame number readable through DSTS;
this is supporting IP-family documentation, not proof of Pi-specific timing:
[ST reference manual, section30.7.2](https://www.st.com/resource/en/reference_manual/cd00225773.pdf).
TinyUSB's DWC2 device implementation also ACKs SOF then reads DSTS, and masks
SOF when its temporary use ends:
[TinyUSB DWC2 device source](https://github.com/hathach/tinyusb/blob/master/src/portable/synopsys/dwc2/dcd_dwc2.c).
The phase correlation and proposed failure attribution are our inference from
the saved Pi traces, not claims those references make about PiSight.
