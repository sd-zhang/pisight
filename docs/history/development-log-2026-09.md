> Historical archive. Candidate statuses, operational instructions and local paths
> below may be obsolete. Use ../../DEBUGGING_NOTES.md for the accepted baseline.

# PiSight USB video and microphone handoff (2026-09-26)

## Latest hardware: audio tuning and diagnostic toggle tested (2026-09-28)

User flashed audio-settings candidate. Read
`diagnostics/capture-audio-settings-20260928/results.md` before more changes.
Mic-on29.960fps,6JPEGerrors/~117s (previous29.951/7). Native20s and90s captures
have continuous48kHz timestamps. UVC gain/cutoffs/bypass apply and applied
readback work; defaults restored. Diagnostics enabled temporarily then disabled;
173542-byte RAM log unchanged after84s. Final desired/saved diagnosticsOFF,
no unsaved settings. No Save requests or SD writes by test; hardware persistence
not exercised. Actual card bytes not hashed independently.

CPU cost: mic9.066% vs prior4.833%; newly deployed filtering/tuning costs CPU.
Total70.5–71.55% in mostly active windows; no fully active aggregate pair, so
not exact comparison to prior67.922%. One late audio arm among140201schedules,
0early,0disabled video payload misses; rare NAK/JPEG errors remain.

Bulk174kB log download during video caused a temporary23.9fps window/14JPEG
errors, then recovered29.964fps for the following minute.90s audio continuous.
No persistent collapse, but don't claim bulk diagnostics never affect video.
Future app should avoid/throttle large downloads during calls. No calibrated
acoustic quality/latency test. All captures finished, diagnosticsOFF, no new
firmware/image/serial/drive writes/playback/commits/pushes this turn.


## Latest candidate: UVC audio settings and optional diagnostics (2026-09-28)

User approved firmware capabilities only, future UVC app later; no host CLI,
web app or serial. Added diagnostics setting at user's request to stop ongoing
SD log writes. Built `diagnostics/sdcard-audio-settings.img`, 41431552 bytes,
SHA256 `244a83b7ad1cad01d9df80f99996fda27e62de0b45a22f3fb88e0a0393186c39`.
Read `diagnostics/audio-controls-tests/results.md` and `docs/uvc-audio-controls.md`.

Existing XU selectors3/4 implement live gain/HP/LP/bypass, requested/applied
readback, peak/clips, RAM defaults and asynchronous explicit JSON Save; one
atomic shared preset and20ms crossfade, no extra audio queue. Default band-pass
unchanged. Diagnostics defaultOFF; enabled snapshots RAM-only, capped4MiB.
Removed automatic SD log/raw-capture copies. Boot rawprobe and detailedmic
snapshots gated. Existing recovery counters/basicRAMlogs remain; cap applies
onlyPISIGHT.TXT. Config startup still seeds/repairs JSON when missing/invalid.

NativeUBSan,ARM1176DSP/controls,actualALSAplugin/route,BusyBoxJSON/save/lock,
UVCdispatch/descriptor,diagnosticrotation and6supervisorcases pass. Packaged
plugin tests pass;96000defaultsamples match reference. Review no blocker after
fork-childstdio andS32bypassrounding fixes. Exactly11rootchanges againstbandpass;
bootpartition/kernel preservedbyte-for-byte. No actualPiCPU/FPS/listening or
hostUVCtuningtest yet. NeverclaimemulationprovesphysicalUSB. Useraloneflashes;
no drives/serial/playback/commits/pushes this turn. Futurecapturesmustenable
newdiagnosticsflag beforeexpectingperiodiclogs; oldcapture scriptsdon'tenableit.

Build volume has final sources/patch0022. Export/extraction:
`/private/tmp/pisight-audio-controls`; Docker `/work/audio-controls`.


## Latest candidate: fixed microphone band-pass (2026-09-28)

User explicitly chose fixed band-pass first, no adjustment, keep simple/test.
Built diagnostics/sdcard-bandpass.img (41423360 bytes), SHA256
71e0ce2413028c196f40ac97aa4b58df0ea20de84485a999c890e9f0baa03637. Read diagnostics/bandpass-tests/results.md.
80 Hz HP + 8 kHz LP, second-order Butterworth each; S32 left-slot mono -> float
DSP -> saturated/rounded S16. Existing ALSA bridge timing/lifecycle unchanged.
No EQ settings/UI/serial/persistence. Exactly two root changes: asound.conf and
new ALSA plugin; boot/kernel and every other root file identical to camera-work.

Native/ARM response, DC/saturation/silence/reset, actual target ALSA plugin,
17/1024-frame reads, same-handle prepare and wrong format tests pass. Packaged
96000-sample capture equals native reference. Supervisor five scenarios pass.
Independent review no blocker. Initial silence-cleanup regression corrected;
synthetic source partial-read failure isolated/fixed, not a firmware transport bug.
UBSan passes; Mac ASan stalled and was stopped, no ASan pass claimed.

Saved recording filtered offline, RMS drops21dB, no clipping; not proof of speech
improvement. User reports mixed feedback and accepts existing sound; this is their
requested filter experiment, not a diagnosed fix. Hardware CPU/FPS/listening still
pending. No flashing, new live capture, serial, sound playback, commits/pushes.
User alone flashes. Docker volume updated; source/exports /private/tmp/pisight-bandpass.

## Latest hardware: camera CPU changes show no meaningful gain (2026-09-28)

User replugged after camera-work candidate delivery. Completed standard capture;
read `diagnostics/capture-camera-work-20260928/results.md`. Full simultaneous CPU
67.922% vs prior68.409%: only0.49percentage points, within plausible scene/run
variation. Physical shutter state unconfirmed, running image not independently
hashed. Do NOT sell microbenchmark savings as demonstrated whole-device headroom.
Mic-on29.951fps,7JPEGerrors/~117s vs prior29.969/5; first2sessions18NAKpayload
misses vs8, zero disabled video payloads, zero active incompleteIRQ. Encoder/source
errors zero. Native20s and post-readback30s audio continuous48kHz; latter29.943PTSfps,
898unique/899callbacks. No persistent major slowdown after existing-XU diagnostics.

No late/early audio enables across readbacks. Final counter interval includes
4additional audio sessions although our post-readback test used one; do not attribute
whole audio delta to our30s capture. Extra opens unestablished. Mic sound quality
and acoustic delay remain unresolved. Hardware zoom/EV changes untested. No new
image/reflash justified by this small CPU delta. No serial/drives/sound playback.
All our capture processes finished; no production edits or builds this turn.

## Latest candidate: camera CPU work reduction (2026-09-28)

User approved trying camera-side redundancies. Built/verified
`diagnostics/sdcard-camera-work.img`,41423360bytes,SHA256
`95ecfd3891d2462178578b7b4f1b33cbe9a2c4c2806867ecf481cb14bdbec267`.
Read `diagnostics/camera-work-results.md`. Gadget0021 submits crop/EV only on
change/start, atomic pending flag retries synchronous and asynchronous cancellation
without losing notifications. Libcamera0002 caches only lens-shading geometry;
current gains/arithmetic remain unchanged. No USB/audio/cadence changes.

Native+ARM1176-emulated lifecycle checks and7,634,088 numerical comparisons pass.
Review caught initial cancellation bug; fixed/tested, final review no blocker.
FullARM/imagebuild passes, exact3rootfileschanged(libuvcgadget,IPA,signature).
Bootpartition/kernel byte-identical to testedcombinedimage. IPA signaturevalid.
Interpolation-only speedup~12%Mac/~4.5%QEMU; NOT actualPi/totalCPUgain. Hardware
CPU/FPS/settings behavior untested. Existing mic rasping complaint unresolved.

Docker volume contains newpatches; exports /private/tmp/pisight-camera-work.
Working sdcard-audio-sof-shutter.img retained. No livecapture/serial/physicaldrive
writes/commits/pushes. User alone flashes. All builds/testsfinished.

## Remaining CPU audit (2026-09-28)

User asks for more CPU headroom. Read `diagnostics/remaining-cpu-audit-20260928.md`.
Current fullactive68.409%, priorsoak66–67%. Fresh savedthreadanalysis: busiestcamera
threads18.754/14.761%,ALSA4.622%,pigpiod0.002%. IRQ13.152% overlaps thread costs.
Source candidates: avoid unchanged crop/EV submission everyframe; cache invariant
VC4lensshading interpolation geometry. Neither cost nor savings profiled yet.
IPA already caps algorithms30Hz; lowering15Hz would trade automatic-controlresponse,
not free cleanup. RawYUVzerocopy alreadydone; JPEGcopyremains. Keep diagnostics:
part of its state now essential to recovery. USB8kcompletion/s structuralcost;
avoid speculative scheduling changes. No production edits/image/reflash this turn.

## Latest: microphone sound quality unresolved (2026-09-28)

User follow-up: sound described as "sandpaper coming through the screen"; no
pre-enclosure baseline. Earlier rawI2S capture recovered and independently shows
strong low-frequency drift before bridge/USB (RMS-32.985dBFS; offline80Hz one-pole
HP-67.571). This does NOT identify rasping cause or prove enclosure blame. Raw
checksum matches originalreadback; rightslotzero, low8bitszero, noclipping.
See mic-quality-20260928/earlier-raw-i2s-analysis.json. No new firmware/livecapture.


User reports mic quality poor. Investigation saved at
`diagnostics/mic-quality-20260928/results.md`. Existing ambient WAV unclipped,
no duplicate10ms blocks; dominates below80Hz (99.75% sampled spectral power).
Independent80Hz highpass lowers RMS to-64.35dBFS vs wholefile-38.29dBFS. This is
low-frequency drift/rumble evidence, NOT yet explanation of subjective complaint.
No controlled speech sample or symptom/app details yet; async question pending.
Source left-slot/unity route and48kHz format checked, no changes. Need separate
sound-quality evidence; prior continuous timestamps are not proof of good audio.
No live recording, playback, firmware changes, serial, drives, or reflash this turn.

## Shutter closure check (2026-09-28)

User physically closed shutter. Host still enumerates iSight camera and iSight
Microphone; plain IOUSB tree confirms iSight connected, and USB diagnostic
readback succeeds. Latest saved target snapshot uptime632.59s still has zero
GPIO26 shutter edge IRQs; only logged shutter state is open. No detected closure
in available evidence; wiring/sensor suspected but not proven. User accepts a
purely physical shutter and does not want this pursued. No source or image change,
no reflash or physical wiring action. Evidence: diagnostics/shutter-closed-20260928.

## Latest hardware: combined SOF + shutter image tested (2026-09-28)

User flashed the combined image. Test complete; see
`diagnostics/capture-audio-sof-shutter-20260928/results.md`. Mic-on29.969fps,
5JPEGerrors/~117s (previous29.959/5), CPU68.409% (previous68.831%). No sustained
throughput/CPU regression observed. Zero incompleteIRQ in full active64.42s;
zero late audio enables across all3sessions. First2sessions8NAKvideo payload
misses,0disabledpayload; rare glitches persist. Native20s and post-readback30s
48kHz audio have0PTSgaps>1ms. Post-readback29.806distinctfps,8repeats/900callbacks;
no lasting large slowdown. Acoustic delay still unmeasured; no chirps played.

Readback confirms expectedSOFpolicy and shutter-S enabled, startup reads OPEN;
GPIO26edge IRQ stays0. Initial setup works, physical close/reopen NOT tested.
Sensor may still be broken/miswired. Do not claim reconnect verified. No new
source/image changes justified by these results. No serial/card extraction/
physical-drive writes. All capture sessions ended; user alone handles flashing.

## Latest combined image: user explicitly requested shutter inclusion (2026-09-28)

This supersedes earlier advice to leave shutter disabled for future images:
user asked "can you roll the new shutter thing in as well" after reporting
sensor may be broken/miswired. Combined candidate ready:
`diagnostics/sdcard-audio-sof-shutter.img`,41423360bytes,SHA256
`2dd46f63008959fae2be32bc008ad6377e37f7466640f86043601edf818b608a`.
See its README.txt and `audio-sof-shutter-image-verification.txt`.

Boot partition/kernel byte-identical to hardware-tested audio-SOF image;
rootfs byte-identical to reviewed/ARM-built shutter-switch image. Repacked
existing hash-verified regular files, no new source behavior changes. Exact
root difference vs tested image is S60,uvc-gadget executable,libuvcgadget; boot
files unchanged. Shutter lifecycle and LED tests pass; compiled source hashes
match. Disconnect path cancels timer/SOF arming before request teardown.

Shutter enabled(-S), GPIO26 high=closed/low=open, edge events50msdebounce.
Closed disconnects whole USB gadget; open reconnects. Initial state is obeyed:
a stuck-high sensor can prevent both camera and mic appearing. User informed.
Actual GPIO and combined close/reopen/performance still UNTESTED. This image
has not been flashed by us; no physical-drive writes, serial, commits or pushes.
Previous tested audio-SOF image preserved. No active builds/capture sessions.

## Sustained follow-up on the same SOF image (2026-09-27)

After user "uh huh", ran180s native simultaneous A/V without another flash.
Read `diagnostics/capture-audio-sof-soak-20260927/results.md`.29.943distinctfps,
6JPEGerrors,7NAKpayloadmisses,0disabledpayloadlosses.8641536 audio samples,
0PTSgaps>1ms. No additional late audio enable: lifetime late count still1.
Both new audio NAKs occurred before ALSA PCM capture began; closure explains
new audio disabled sample. Two full active target windows still0incompleteIRQ,
0audioNAK,CPU66–67%. Remaining video glitches are sparse NAK-path misses.

Diagnostic snapshot correlation did NOT repeat: none of6 errors overlaps
inferred snapshot work, unlike4earlier clustered errors. Do not remove logging
or build another speculative firmware change from that lead. Existing samples
cannot identify the exact blocking handler/critical section or DMA delay.
Asked user whether Pi mic can hear Mac speakers for a brief acoustic-delay test;
no answer received, no sound played. Actual delay still unmeasured. Shutter
sensor suspected broken/miswired; leave monitoring disabled. All tests finished,
no new image or production edits, no serial/drive writes.

## Latest hardware: SOF scheduling removes recurring recovery corruption (2026-09-27)

User flashed/replugged audio-sof image; test complete. Read
`diagnostics/capture-audio-sof-20260927/results.md`. Policy confirmed
interval8/lead1/timer_lead2/sof1. Mic-on29.959fps, JPEG69→5 over comparable
~117s windows; video failed payloads89→10, disabled payload80→0. Full active
64.46s window: incompleteIRQ1000/s→0, CPU68.831%, gadgetIRQ8770/s. Strong
hardware support for premature audio enable/shared recovery as major remaining
video corruption mechanism. Still occasional NAK misses, including mic-off.

Native20s and post-readback30s audio continuous48kHz; post-readback~30fps,
899distinct/899callbacks, no persistent degradation. One late audio enable in
second native session (none in first120s or later30s); precise timestamp not
logged. Latest initial-session audio NAK occurs before PCM bridge startup;
do not claim proven lossless audio or acoustic delay. Strict zero-new-late
criterion not met. Acoustic latency and suspend/resume remain untested.
No new image/source fix this turn; no immediate reflash justified by counters.

User says shutter sensor likely broken/miswired and physically OPEN. Current
image keeps monitoring disabled. Do not silently reintroduce untested shutter
patch0020/-S in a future image: Docker default rootfs still contains it, whereas
this verified candidate uses saved LED rootfs. Keep the working baseline.
No serial, drive writes/card extraction, or chirps. All capture sessions ended.

## Latest USB candidate: frame-aligned audio enable (2026-09-27)

User redirected work to remaining simultaneous A/V reliability. All16 bounded
video recovery selection samples occur at audio poll phase−1. Existing lead3
permits an earlier same-parity audio slot; hypothesis is its incomplete event
spills into video recovery. Do not claim every80disabled payloads is explained.
A constant-only lead1 change was rejected for inherited0–125us timing margin.

Kernel0011 instead wakes timer at target−2 and temporarily enables SOF IRQ,
arming only in target−1. Shared-mask, request/session/epoch/power checks and
NAK ownership preserved; NAK reschedule skips SOF waiter. No continuous SOF
interrupts. See `diagnostics/audio-sof-design.md` for design, evidence and limits.
397127 native+ARM checks,101 recovery,26 incomplete,11 sampling and458752age
checks pass; independent review no blocker. Deferred minor: end-to-end suspend/
resume mask test. Cancellation must precede inaccessible power state. Hardware
timing/performance/audio continuity not yet verified.

Built/verified isolated `diagnostics/sdcard-audio-sof.img`,41419264bytes,SHA256
`4e24ecde63ef34d3844cfee556c1c0c2906a68ccde075f13e81c7a087394f89a`.
Exact LED-events rootfs; only boot ZIMAGE differs. Excludes untested shutter0020
for a clean comparison; shutter image remains separate. Policy readback:
`irq_arm_policy interval=8 lead=1 timer_lead=2 sof=1`.
Docker kernel already patched0011; gadget still has0020. Default full build
would bundle both; this candidate was repacked with saved LED rootfs. No active
build. User alone flashes; no serial/physical-drive writes. Actual Pi unchanged.

## Latest candidate: simple interrupt-driven shutter soft switch (2026-09-27)

User approved shutter closed=USB camera+mic unavailable, open=reconnect, with
negligible idle CPU; emphasized simplicity. Patch0020 integrates GPIO26 v2 edge
watching into the existing camera event loop with50ms kernel debounce, no new
worker/service/timer. Uses UDC soft_connect; stops camera and gates stale starts;
existing UAC2/mic supervisor stop audio on disconnect. Reads initial state before
advertising, so a closed shutter needs no initial toggle. Kernel and diagnostics
unchanged. Read `diagnostics/shutter-soft-switch.md` for verification/limits.

Built and image-verified `diagnostics/sdcard-shutter-switch.img`, 41423360 bytes,
SHA256 `5634e3a8699b2944ebd9fd25fc42c27435c79a61ceed59a215c25b3f258c8a51`. Native+ARM boundary tests, lifecycle/partial-start tests, LED and
settings integration pass. Old toolchain GPIO header issue resolved with exact
pinned-kernel UAPI copy; partial-start cleanup regression corrected. Three root
paths differ from LED-events image; all boot files unchanged. Physical shutter,
CPU overhead and repeated host reconnect UNTESTED. Successful soft_connect write
does not guarantee re-enumeration. User alone flashes. No serial/drive writes.
No active build; Docker volume already contains final patch0020. Actual Pi still
runs LED-events image with29.4fps simultaneous A/V and residual USB errors below.

## Latest hardware: cleanup restores near-30-fps simultaneous capture (2026-09-27)

User flashed/reconnected the combined LED-events candidate. Test completed;
read `diagnostics/capture-led-events-20260927/results.md`. Mic-off/on/off video
29.988/29.392/29.929 distinct fps (previous 24.593/20.594/25.605). Full active
snapshot CPU 69.552% (previous 94.888%); pigpiod runtime ~0.002%, previous ~11%.
Host name iSight Microphone works. Native combined audio continuous at 48 kHz;
physical acoustic delay remains unmeasured. Post-XU-readback combined 29.478 fps
with continuous audio: no persistent slowdown observed in that 30-second check.

NOT fully fixed: 69 mic-on JPEG decode errors, 89 failed video payloads (previous
74/93). Gadget IRQ/handler rates essentially unchanged. Encoder errors zero;
24 deferred requests completed, audio timers all armed, none late/early/resync.
CPU headroom restored; remaining USB reliability needs separate investigation.
No new candidate/image or source change this turn; do not reflash by habit.
Diagnostics retained. No serial/card extraction/drive writes. Capture sessions
finished. Exact running image hash not read independently; name and target
process state match cleanup. Do not overattribute gains to one bundled change.

## Latest candidate: event-driven LEDs, diagnostics retained (2026-09-27)

User authorized trimming more waste while retaining diagnostics. Patch 0019
moves logo off/on/activity handling into the gadget's stream/settings events,
removes the once-per-second shell/pigs helper, and applies mode on startup and
successful settings saves. See `diagnostics/led-events.md`.

Latest combined image: `diagnostics/sdcard-led-events.img`, 41419264 bytes,
SHA256 `fef43927dda8e11f6d38ef9b16a3da2f8367909aa2c75dabdec5f13d53facbf5`. Includes prior camera logging correction, shutter removal,
pigpio -m and exact iSight Microphone naming in both modes. ARM build, focused
LED tests, BusyBox settings integration, review and image verification pass.
Only service, gadget executable/library and deleted helper differ in rootfs;
boot files and diagnostics are unchanged. Physical LED behavior and CPU/FPS gain
remain unmeasured; simultaneous A/V is not claimed fixed. User alone flashes.
No USB serial or physical-drive writes. Docker volume already has patch 0019;
no active build. Actual Pi still runs the earlier patch 0009 image.

## Camera logging correction built and image verified (2026-09-27)

Latest combined image: `diagnostics/sdcard-camera-cpu-fix.img`,41419264bytes,
SHA256 `51899753b7252a0d74215050b02f3d15bd4b4fc5f84f3a0c7b551a217e168c19`.
Includes shutter removal, pigpio-m, and exact `iSight Microphone` in both USB
alternate settings. User alone flashes. No new flash was needed to identify
and reproduce the CPU waste below. HardwareCPU/FPSgain remains unmeasured.

Read `diagnostics/libcamera-suppressed-log-investigation.md`. Exact libcamera0.5
LOG macro constructs messages/prefixes and evaluates all stream operands before
its destructor filters DEBUG below defaultINFO. These calls occur throughout
CameraManager/IPA/AWB. ActualARMlibrary offlineprobe confirms20000suppressed
messages still format20000values, while guardedheaderformats0. This is software
reproduction underqemu-arm1176, not Pi performance emulation. Do not convert its
isolated elapsed0.2007→0.00038s into totalCPU/FPSsaving. See libcamera-log-probe.cpp
and libcamera-log-*.txt. Enabled/dynamic/default/member/static/ifelse cases pass;
Fatal above threshold100 andASSERT(false) exit134; core dumps disabled.

Active patch: board/raspberrypizero/patches/libcamera/0001-skip-suppressed-log-formatting.patch,
through existingBR2_GLOBAL_PATCH_DIR. Earlycategoryguard plusvoidifystream keeps
Fatalunconditional. LOGyieldsvoid andskipsoperands; documented. No existingABI
layout/signature changes. Firstfullbuild caught staticderived qualifiedLOGlookup;
reproduced andfixedwithlocal `using libcamera::_log;` in V4L2Device::fromColorSpace
andCameraSensorRaw::match. OrdinaryLOGcalls now usedthere. Header's qualification
semantics are not universallysourcecompatible; no otheraffectedcalls found.
Independentreviewverified approach. Initialbuild logpreservedwith-first suffix.

Final fullcamera/IPA/gadget ARMbuildexit0, no compilererrors/warnings, eightknown
Buildrootinventorycommnotices. Compiledfourfilehashesmatch, patchapplyexact.
IPA signatureverifiedafterinstall/strip. Probeagainstrebuiltlibrarypasses.
Packagedrootfs has exactlyfivechangedcamera artifacts vsrenameimage: base.so,
libcamera.so,IPA.so,IPA.sign,proxyhelper. Boot/kernel byte-for-byte unchanged.
`verify-camera-cpu-image.py`,camera-cpu-image-verification.txt record checks.
Source `/private/tmp/pisight-log-cost/{base,new}`; exports/rootalso there.
Docker volumealreadyhasappliedlibcamerapatch; do notapplytwice. No activebuild.

Latest actualhardware remains patch0009. See capture-audio-arm-20260927/results.md:
combined~20.6fps, CPU~95%, audio bridge~4%, pigpiod~11%, busycamerathreads.
Per-thread roles mostlyinferred, no functionprofiler. These costs overlapIRQ
attribution and are not an additiveCPUbudget. ExistingXUreadbackworks; no serial,
SDextraction, commits,pushes orphysicaldrivewrites. Acousticlatencyunmeasured.
Host probes defaultnewmicname; overridePISIGHT_MIC_NAME='Capture Inactive' for
currentoldfirmware. Next hardwarecheckshouldcapturebothstreams andreadbackafter.

## Microphone name requested: iSight Microphone in both modes (2026-09-27)

User explicitly requested the exact USB audio name `iSight Microphone` for BOTH
active and inactive modes. Kernel patch0010 uses configured function_name for
all AS interface alternate-setting strings; package patch0018 sets function,
control and microphone terminal/channel/volume names before bind. ARM build exited0;
verified `diagnostics/sdcard-isight-microphone.img`,41394688bytes,SHA256
`bac27053bfcf8e788c8f38e9a5cf4734fb8ef6f81937cd0c8693b7fa258eadf8`. Rootfs differs only in gadget setup script;
boot differs onlyZIMAGE fromno-shutter. Driverobjecthasnooldidle/active labels;
compiledsourcehashesmatch. Reviewno blockers; host display not hardware-checked.
Build log `diagnostics/build-isight-microphone.log`, source `/private/tmp/pisight-mic-name`.
Includes shutter removal; previous `sdcard-no-shutter.img` lacks the rename.
Host probes now default to `iSight Microphone`; set PISIGHT_MIC_NAME='Capture Inactive'
when measuring older firmware. No timing or audio format change in this rename.

## Patch0009 hardware tested; shutter-free image built (2026-09-27)

Latest tested image is `diagnostics/sdcard-audio-arm.img` (SHA256
`ae709600d0fe284c9e9d17bf0043271bb23d66177c2e4d48113087236941b5c2`).
Read `diagnostics/capture-audio-arm-20260927/results.md`. Preflight confirms
`irq_arm_policy interval=8 lead=3`. Mic off/on/off:24.593→20.594→25.605fps,
0→74→0JPEGerrors. Native combined20.640fps; post-readback19.600fps. Audio
PTS continuous; acoustic delay unmeasured. Payload misses93 vs322previously,
exactly reconciled to UVC. IncompleteIRQ/s997 vs3987, totalgadgetIRQ/s9733;
handler13.21%,CPU94.89%. Timers140190scheduled,1late,0resync; callback elapsed
~0.60% in full active window. Lower interrupt count did not reduce total CPU.
Smooth simultaneous A/V remains unsolved.

Per-thread evidence points to camera processing and GPIO overhead, not a95%
audio bridge: alsaloop~4%;pigpiod~11%. Generated libcamera source and thread
creation timing suggest141=CameraManager,142=AWB,143=ALSC,909=encoderoutput,
910=hardwareencoder,917=IPAprocessing. Only141has explicit log TID evidence;
others are inferred mappings, not stack profiles. Camera scheduling wait is
substantial; do not equate high use with an inherent Pi hardware limit.

User explicitly ordered removal of the shutter monitor. New patch0017 removes
sensor setup/read/filter/callback, frozen-frame handling, and sensor CLI use.
Both S60scripts use23/24LEDpins. Legacy3-pininput accepts but ignores third.
`etc/default/pigpio` now `-t 0 -m`: no alert CPU thread, LEDs retained. DMA and
a blocked client notification thread remain; retainPWMclock to avoidI2Sclobber.
NativeLED checks failbaseline2cases, passnew2; independentreviewno blockers.
ARM build exited0; image verified: `diagnostics/sdcard-no-shutter.img`,41394688bytes,
SHA256 `20b1ad04c5f7674d67d34fded498988956fc9186f40303e36e38bf3bbd5af9c5`.
Boot/kernel bytes unchanged from patch0009. Rootfs changes exactly4files:
etc/default/pigpio,etc/init.d/S60uvc-gadget,usr/bin/uvc-gadget,usr/lib/libuvcgadget.so.0.4.0.
Compiled5sourcefile hashes match reviewed sources. Build retains one existing
unused-function warning in uvc.c and four Buildroot inventory comm notices.
See `diagnostics/no-shutter-removal.md`, `diagnostics/build-no-shutter.log`.
Sources `/private/tmp/pisight-no-shutter/{base,new}`. No hardware savings yet.
No new USB/kernel/encoder policy change in this removal. No physical-drive writes.

## Delayed audio enable candidate built; hardware untested (2026-09-27)

Current candidate: `diagnostics/sdcard-audio-arm.img`, 41398784 bytes,
SHA256 `ae709600d0fe284c9e9d17bf0043271bb23d66177c2e4d48113087236941b5c2`.
Kernel SHA256 `cca151e3f09c0ed0b72bdedb507cc8337062f9c2f63124e277c2a6d94a1c24b7`.
Patch0009 prepares interval8 HS buffer-DMA IN requests normally, delaying only
EPENA until approximately target−3. Expected net ~2000 fewer interrupt/timer
events/s, not a measured FPS improvement. See `diagnostics/audio-arm-design-and-results.md`
and `diagnostics/sdcard-audio-arm.README.txt`. Latest actually tested firmware is
patch0008, with results in the next section; it still fails simultaneous A/V.

Native checks:32 scheduling,97 recovery/lifecycle,26 incomplete,11 sampling,
458752 timing assertions. Review findings (runtime hres, resync wrap phases,
giveback epoch/power) reproduced and fixed; final independent review no blockers.
ARM build exit0, no compiler errors/warnings. Four existing nonfatal Buildroot
inventory comm notices. Checkpatch0errors/0warnings with --no-tree --no-signoff.
Clean patch application exact; compiled source hashes match reviewed sources.
Packaged rootfs inventory unchanged and only boot ZIMAGE differs from patch0008.

Source snapshots `/private/tmp/pisight-audio-arm/{base,new}`; ledger progress.md
there. Active patch in webcampi board linux-patches0009. Build volume updated.
No commit/push/physical-drive writes. User alone flashes. No new hardware capture
yet. Next reconnect: verify `irq_arm_policy interval=8 lead=3`, run standard
combined capture, retrieve logs afterward. Compare TOTAL IRQ/CPU including timer
callbacks and late/resync counts; gadget-handler time excludes timer work.
Acoustic mic delay still unmeasured. Optional speaker-chirp feasibility question
was sent, unanswered; do not play sounds without that answer. No serial.

## Patch0008 hardware tested: real transfers saved, combined A/V still fails (2026-09-27)

Read `diagnostics/capture-incomplete-fix-20260927/results.md` first. The device
now exposes patch0008 counters. All334 deferred requests completed successfully;
failed video payloads322 versus690 previously, exactly reconciled to UVC.
Mic off/on/off25.759→19.807→26.086 distinctfps and0→220→0 JPEGerrors.
Native combined17.724fps, continuous audio timestamps; acoustic delay unmeasured.
ALSA active queues median49.823ms. Encoder failures0. Extra~4kincompleteIRQ/s
remain; full active CPU94.81%,gadget IRQ12661/s,handler12.95%.

The232-request audio NAK burst was during shutdown, after video STREAMOFF,
not in the sustained combined interval. Post-readback30s combined capture
18.977distinctfps with continuous audio shows no additional persistent slowdown.
Main target logs exclude that later check. No serial or physical-drive writes.

Next investigation is delayed audio endpoint arming to reduce excess incomplete
interrupts. High-resolution timers are enabled, but timer phase/lateness and
request ownership must be proven before implementation. A naive target−1 timer
and simply changing video interval were rejected as insufficiently justified.
No new scheduling patch/image exists yet. The following sections are historical;
statements that patch0008 is untested no longer describe the current state.

## Guarded incomplete-event correction built; hardware untested (2026-09-27)

Next candidate: `diagnostics/sdcard-incomplete-event-fix.img`,41398784bytes,
SHA256 c03c1a3c25a78d6caba028e2336da4e97604a3e8f8d8ae447f7b5a097a26c45e.
Kernel patch0008 corrects old-event attribution using ACK-first/readback,
pre-EOPF bounds at ACK/decision, deferred request identity, and wrap-safe
recovery. A later EOPF is never cleared by a tail W1C. It depends on patch0007's
timing/arm state. See `diagnostics/incomplete-event-fix.md` for full design,
evidence, caveats and tests. Extra~4kIRQ/s remains; do not promise fullFPSfix.

Final actual-source checks:26 interrupt/epoch cases,22 request/queue cases,
11 sampling cases and458752 predicate assertions pass. Baseline fails4/26.
Independent review caught a reset-during-decision race; reproduced4 failing
transition cases, corrected with shared epoch validity plus identity recheck.
Final independent review found no blocking issue. ARM buildexit0; no compiler
errors/warnings, four existing nonfatal Buildroot inventory notices. Checkpatch
has0errors/4block-comment-format warnings (exit1), not a clean style check.

Compiled source hashes match reviewed source. Packaged kernel/rootfs verified;
rootfs inventory identical to prior IRQ diagnostic image, only bootzImage
changes. Linux build volume now has patches0007/0008 and corrected source.
No commit/push/physical-drive write. Image not flashed yet. Next target test
must measure simultaneous camera/mic, with full log retrieval afterward;
verify new `irq_recovery` counter line first. Need acoustic latency measurement
in addition to sample continuity. Current hardware still runs diagnostic-only
patch0007 and fails combined capture. User alone handles flashing.

## IRQ diagnostic hardware results: simultaneous A/V still fails (2026-09-27)

Latest evidence: `diagnostics/capture-irq-cause-20260927/results.md` and raw
logs beside it. Existing-XU USB retrieval now works on hardware; do not ask
for card extraction. Mic off/on/off:23.314→18.307→25.302 distinct fps,
0→432→0 JPEG errors. Native combined16.117fps; audio samples contiguous but
acoustic latency unmeasured. ALSA queues median49.542ms. Encoder errors0.
690 payload misses reconcile exactly with UVC summaries. Goal remains smooth
video AND low-delay microphone simultaneously; neither solo-video recovery
nor diagnostics is acceptance.

New evidence:560410 incomplete IRQ observations, roughly4/audio completion;
462 current-target disable selections before current EOPF timing bound.
First selection matched to actual video retirement before that deadline:
previous frame12912 sampled at80632345000ns, decision80632397000ns,
retirement80632415000ns at live=target12913. This establishes a specific
premature recovery path under documented timing assumptions, not proof of
preventable host-token loss or a complete explanation of the FPS deficit.
Guarded deferral is being reviewed; ACK order, later-EOPF recovery, and wrap
must be tested before any performance candidate. No new fix image yet.

The user warned serial previously caused persistent FPS loss. There was one
XU preflight read before this capture; full retrieval followed measurements.
Post-readback video-only23.845 distinct fps, no repeats; no persistent18fps
state reproduced. Instrumentation overhead/scene differences remain caveats.
Do not open USB serial, flash drives, commit, or push. Continue authorized
analysis/fixes without treating this diagnostic result as completion.

## Targeted interrupt-cause candidate ready, not hardware tested (2026-09-27)

Continued source investigation and independent review identified a selection
ambiguity: a global incomplete-IN event delayed across SOF can select a pending
current-frame video request, but existing retirement samples cannot distinguish
that from a real miss. The nine-case native replay demonstrates that ambiguity,
not a measured hardware race. A naive strict-past comparison was rejected by
two counter-wrap failures even with simulated next-poll NAK recovery.

Prepared diagnostic kernel patch0007 to gather global/endpoint IRQ counts,
gadget-handler duration, bounded disable-decision snapshots, and request-arm
frame brackets. A conservative timestamp bound can identify an incomplete event
observed before the current frame's EOPF under documented controller assumptions.
It does not establish audio origin or pre-token cancellation. Measurement
overhead and coverage limits are explicitly documented.

Verified image: `diagnostics/sdcard-irq-cause-diagnostics.img`, 41,398,784 bytes,
SHA256 `a2d2ba2032750a79338960732bf45b38c464fc2e33b8fb5d55af970845f36b0b`.
Includes existing XU log retrieval, allowing automated capture to attempt USB
readback afterward. Rootfs inventory is identical to held USB-readback image;
only its kernel changes. Transfer recovery and audio/video endpoint settings
are unchanged. Build exited0, source hashes match, partition/kernel/rootfs
verification passes. Native predicate458752 assertions, sampling11 scenarios,
recovery19 cases pass; independent review has no outstanding blocker.

Read `diagnostics/irq-cause-diagnostics.md` for precise counter meanings and
`diagnostics/irq-cause-image-verification.txt` for artifact evidence. No hardware
test yet and no confirmed root cause or performance fix. The previous
USB-readback-only image remains held. User handles any flash; no physical-drive
writes, commits or pushes were made. Do not ask for another card extraction as
the default next step.

## Patched-kernel card verified; transport failures remain (2026-09-27)

Read-only card copy `diagnostics/target-coalesced-fix.log`, SHA256
61ae7f5d2102049e81a0cf1db5a08eeb1e3309c75b27016387d8f3bda9387199.
Mounted kernel matches candidate exactly. Disabled misses1255/payload676,
NAK614/payload6; total682payload/1187empty matches UVC summaries. No sampled
future-target discard remains; intermediate0x3 sample has current=target5109.
This is sampled evidence, not proof about every event. Host performance unchanged.
Full active CPU94.18%,USB IRQ12810/s, almost identical to prior94.01%/12792/s.
Active ALSA median49.72ms (range45.25–69.92), bridge~3%CPU. No encoder failures.
Exact initiating failure remains unproven. Details/reproducible scripts in
`diagnostics/coalesced-readback-results.md`. No physical drive writes.

Built diagnostic XU selector2 readback to avoid further card removals for
logs; source patch0016 and host reader `diagnostics/read-usb-diagnostics.py`.
It adds no interfaces/streaming endpoints and is NOT a performance fix. Verified candidate `diagnostics/sdcard-usb-log-readback.img`,41398784bytes,
SHA25663995b85fcd6601b0673935f08ed88c076133dac651d0d3f62dd155309ec8b09.
Kernel/boot files unchanged; rootfs changes only libuvcgadget and setup script.
See `diagnostics/usb-log-readback.md` for validation and limitations. Existing flashed
image lacks selector2. Do not claim readback works on hardware before testing.


## Coalesced-fix hardware trial still fails simultaneous A/V (2026-09-27 16:01–16:04)

User reported reflashing/replugging candidate. Named iSight enumerated480Mb/s.
Repeated identical150s720p mic-toggle/20s native combined capture:
26.409→19.487→26.464 changedfps,0→457→1 JPEGerrors in stable windows.
Previous26.181→19.422→26.293,0→462→1: no meaningful improvement. Native combined
17.601uniquefps (350unique,245repeats); audio960512samples/20.0107s, noPTSgaps>1ms.
Acoustic delay remains unmeasured. This patch does not resolve the user's issue.
Do not present offline replay success as hardware success or build another
speculative image. No target setting changes or drive writes in this turn.

Artifacts: `diagnostics/capture-coalesced-20260927/{results.md,summary.json}`.
Capture script includes70s diagnostic save window; final events.jsonl marker
records its completion. Target PISIGHT.TXT from this boot is the next evidence
needed to compare disabled/NAK paths and whether the sampled premature expiry
was removed. Exact running kernel not independently verified from USB identity.


## Card readback: confirmed premature USB request retirement (2026-09-27)

Read and preserved latest card log as `diagnostics/target-transport-diagnostics.log`
(SHA25659a3d620e6f8bab2c6075b61a85dbdcfed6662354d9825c946d08cf075dff834).
New diagnostics confirm buffer DMA, not DDMA. All719 payload and620 empty UVC
misses reconcile with endpoint disabled/NAK counters. First disabled snapshot:
current2361,target2362,overrun0,IRQ0x3. This is a future request being discarded.
Normal completion precedes disabled recovery in source; extracted production
functions reproduce retiring A, starting B, then flushing/failing B. Only the
first sampled event establishes premature retirement; do not attribute all
1,316 disabled misses to it or claim full FPS root cause is solved.

Applied narrow kernel patch0006: coalesced EPDISBLD prevents normal isoc IN
completion, so disabled recovery owns the original request. Conservative
ENODATA tradeoff; may still lose another expired request on the following NAK.
No descriptor/audio/encoder/timing-trial change. Original replay fails9/19;
corrected replay passes19/19 with UBSan, including later NAK/queue progress.
Independent reviewer found no blocking issue. Full details and limitations:
`diagnostics/coalesced-usb-fix.md`. Verified candidate `diagnostics/sdcard-coalesced-usb-fix.img` is41,394,688bytes,
SHA256c969e4fffa84b50388fb617d2a7aa975e740aad3107ea602b7b8754e84f79d69.
Build exited0; packaged partitions/hash verified; rootfs inventory unchanged,
FAT file inventory changes only ZIMAGE. Hardware performance remains untested.
Docker volume now contains patch0006. Candidate details recorded there.

28 periodic active microphone snapshots show ALSA combined delay42.96–50.04ms,
median49.09ms; bridge3.14–3.46%CPU, frequency1GHz. Audio recovery misses coincide
with two opens/two closes. This does not measure acoustic/host latency or
explain the user's much larger delay. Raw/summary evidence is preserved.
Never write physical drives; user flashes. Do not repeat the old trial or claim
simultaneous A/V works based on these offline checks.




## Diagnostic image reconnected; host capture reproduced failure (2026-09-27 15:39–15:42)

User said replugged after receiving the diagnostic image. Camera iSight and mic
Capture Inactive enumerate. `diagnostics/run-concurrent-capture.sh` successfully
ran150s video with120s mic in the middle, then20s native combined. Stable-window
changedfps26.181→19.422→26.293; JPEG decode errors0→462→1. Toggle decoder3072
completed/484dropped. Native reopen18.059uniquefps; audio960512 samples20.0107s,
zeroPTSgaps>1ms. Acoustic delay still not measured. No settings changed.

Results: `diagnostics/capture-transport-20260927/{summary.json,results.md}`.
FFmpeg WAV106.837sample-seconds over120timestamp-seconds repeats the earlier
shortfall; its v9.0.1 AVFoundation callback overwrites pending audio frames, so
host recording loss is a candidate. Do not infer Pi audio loss from this alone.
Next required evidence is target PISIGHT.TXT readback after the save window.
No further flash requested. Confirm diagnostic snapshot and isoc_stats contents
in that log before claiming the image was running or a specific driver cause.

## Diagnostic evidence gap closed in source (2026-09-27)

After the user explicitly told the agent to continue, further source checks
ruled out an unbounded UVC request pool (capped at64) and showed alsaloop selects
the gadget playback-pitch control. Existing microphone-window JPEG failures
occur between periodic SD writes. These exclusions do not identify the initiating
USB fault or measure the reported microphone delay.

Built **diagnostic-only** image: `diagnostics/sdcard-transport-diagnostics.img`,
41394688 bytes, SHA256
`de63a4179bced85db70328d57db6cdf5d51f0240e86c28fcf8012bb654a9efd2`.
It preserves the flashed audit image's2048-byte/125us video configuration.
Rootfs inventory changes only `usr/bin/pisight-mic` and
`etc/init.d/S62pisight-diagnostic`; kernel adds bounded DWC2 recovery evidence.
Active package patch0005 records per-path drops, largest recovery burst, and
first/latest/worst burst-start frame/IRQ state through read-only debugfs. No
IRQ printk, frame arithmetic, recovery decision, encoder, or audio setting change.
Microphone snapshots now run during active bridge sessions (1s then every5s),
with a separately labeled pre-stop snapshot, capped512 per supervisor process.
Logger retains incremental microphone log contents instead of the last80lines.

Matching BusyBox hush log-retention tests, five actual-supervisor/fake-ALSA
lifecycle tests, extracted actual DWC2 helper tests, ARM cross-build, and image
partition/hash/rootfs comparisons pass. Independent review's per-burst copying
and labeling comments were addressed. Kernel contains isoc_stats_show. Verifier:
`diagnostics/verify-transport-image.py`; results in
`diagnostics/transport-image-verification.txt`. Final build has no reported
compiler warnings/errors; apparent ERROR text is an unevaluated build guard.

No hardware test or physical-drive write performed. Pi SD remains mounted on
Mac (`/Volumes/NO NAME`), so active driver state cannot be recovered from here.
The diagnosis remains incomplete. This image captures missing evidence; it is
not a performance fix. The previous1024/250us timing trial remains on HOLD.
Docker source/target/output now contain this diagnostic build, not that trial.

`diagnostics/run-concurrent-capture.sh` automates150s video with120s mic in the
middle,20s native simultaneous capture, and70s for the next target log save.
Syntax checked; not executed against the disconnected Pi. Full diagnostic
semantics/limits: `diagnostics/transport-diagnostics.md`. Do not repeat the old
20s trial and miss every active ALSA snapshot again; do not claim acoustic delay
from continuous host timestamps or claim the helper wrap probe proves causation.

## Timing trial on HOLD after user review (2026-09-27)

Do not recommend another flash yet. The user challenged the certainty of the
250us hypothesis and repeated manual experiments. Missed USB transfers are
confirmed; their initiating cause and active microphone latency are not.
The timing trial changes transaction count and cadence and is not sufficiently
isolated to justify another card cycle now. Image remains available only as a
held experimental artifact; see its adjacent HOLD.txt. Continue source/log
analysis. A helper-level wrap probe has been recorded, but independent review
found normal IRQ paths guard against its injected state; target reachability
is unproven. Do not call the16384-like count or old2018patch a diagnosis.
Details in `diagnostics/usb-timing-investigation.md`. Acknowledge that eventual hardware validation cannot be replaced by
static tests, without treating the user as an unlimited test operator.

## USB transport diagnosis and controlled timing trial (2026-09-27)

Simultaneous working video and low-delay audio is mandatory; user explicitly
rejected camera-only success and requested continued root-cause work.
Readback `diagnostics/target-audit-fixes.log` (138372 bytes, SHA256
`280d99ab778251f4bf5672b39875351cfc6e9220bdae636c0b9213d9e3ea3430`)
confirms per-stream missed USB payloads103/79/19, while encoder errors,
corruption flags/invalid lengths, timeouts/resets and source drops are zero.
First stream1504 source submissions match1504 host decoder submissions, of
which1424 completed and80 dropped. Encode mean13.24ms; source production still
averages~25fps over60.267s. This is a USB transport failure with additional
source-rate shortfall still not localized; do not claim all FPS/latency solved.
Mic bridge starts/stops3/3 and all periodic PCM snapshots are closed. Those
snapshots missed active audio: run both streams for>=120s next time.

Built and verified controlled test image: `diagnostics/sdcard-usb-timing-trial.img`,
41394688 bytes, SHA256
`2f6316aeac6450133bece3817a8adabf6584bf347ac6581ce61bded3365ea4fd`.
Only rootfs change from audit image is `usr/local/bin/uvc-gadget.sh`; kernel,
encoder and mic binaries are byte-identical. UVC patch0015 changes maxpacket
2048/interval1 to1024/interval2, allowing250us rather than125us service. Both
camera and microphone remain enabled, same formats/quality/advertised30fps.
This tests endpoint scheduling pressure; cause is not proven and high-detail/
larger-mode throughput is not established. Transaction count also changes, so
a positive result will not isolate cadence alone. Full rationale and evidence:
`diagnostics/usb-timing-investigation.md`.

Actual-script/kernel-descriptor regression fails baseline and passes candidate,
including matching target hush. It catches f_uvc forcing interval1 for2048 even
if interval2 requested. Independent review found no endpoint/probe blocker.
Build `uvc-gadget-reinstall all` exits0. Existing incremental file-list comm
warnings remain; rootfs inventory, source script match, packaged FAT16 kernel,
packaged squashfs and export hashes verified independently. Verifier:
`/private/tmp/pisight-verify-usb-timing.py`; log `diagnostics/build-usb-timing-trial.log`.
Initial root extraction omitted /dev symlinks; restoring only those archived
symlinks resolved the inventory check without modifying the image.

No physical drives written. User has not flashed the timing trial yet. Card
was mounted on Mac for readback. Next action requires user flash/replug; then
measure combined720p+48k audio for>=120s and controlled mic-toggle, plus physical
or perceived delay. This is a trial, not a claimed fixed image.

## Audit-fixes image hardware trial (2026-09-27, 14:39–14:42)

User reports flashing `diagnostics/sdcard-audit-fixes.img` and reconnecting.
Both iSight and Capture Inactive enumerate. Native capture confirms actual
1280x720. One uninterrupted 60-second video trial with mic open in the middle:

- Mic closed before: 24.462 distinct fps, 0 JPEG decode errors (15.33 s).
- Mic open: 21.044 distinct fps, 56 JPEG decode errors (16.63 s).
- Mic closed after: 26.552 distinct fps, 1 JPEG decode error (17.32 s).
- Whole stream: 1423 distinct images, 23.986 fps; host decoder 1424 completed,
  80 dropped. No consecutive repeated images in this video-only probe.
- Reopen camera + mic together: 19.630 distinct fps; 595 callbacks include
  206 repeated images. Native 48 kHz audio: 960512 samples over 20.0107 s,
  zero timestamp gaps over 1 ms. This is not acoustic latency measurement.
- Toggle audio WAV has changing samples (9914 distinct values, RMS910 in
  signed16), but only 850432 samples/17.72 s across FFmpeg's 20 s timestamps.
  That shortfall is not yet localized; native reopen audio does not reproduce it.

Video-only rates improved relative to previous trials, but scene/exposure are
not controlled across builds. Active-mic JPEG corruption remains. Do not claim
hardware fix complete or schedule another flash without target counter evidence.
Those target counters have now been read back; see the USB transport section above. User asked about perceived microphone delay; pending.
Results: `diagnostics/audit-fixes-host-results.json`; host decoder log:
`diagnostics/audit-toggle-usb.log`. Raw host capture in
`/private/tmp/pisight-pwm-test/audit-*`. No physical drives written by agent.

## Completed audit corrections and verified candidate (2026-09-27)

The findings were implemented, not merely recorded. New candidate:
`diagnostics/sdcard-audit-fixes.img`, 41,394,688 bytes, SHA-256
`0a69a8605ed87fcf707f01f42318def9d1cd8231b9982f407b0c1a0df19b4327`.
The old `sdcard-mic-gating.img` remains withdrawn. The user has now flashed this candidate; hardware trial results are above.

- Both S60 copies use explicit supported exports. The real settings/init test
  runs under matching hush with real jq, validates all six values in gadget and
  daemon children, successful persistence preserving other fields, and failed
  JSON-update cleanup preserving the old file. Baseline failed; fixed passes.
- Kernel patch0003 restores UAC2 active state on resume from enabled endpoints;
  it does not restart endpoints. Supervisor refreshes on relevant rate events,
  handling coalesced close/open and draining startup events. Five process tests
  plus extracted real kernel callback tests pass.
- UVC patch0014 drops/recycles failed frames before UVC QBUF, rejects ERROR flags,
  bad lengths/offsets/truncation, resets uncertain codec queues, reopens/configures
  for subsequent frames, and bounds nonblocking DQBUF waits with cancellation.
  Atomic stop flags and protected main-loop completion dispatch fix the races;
  workers join before camera requests are freed. Pipe read/write/drain retry
  EINTR and log genuine errors once per stream. Actual-code fault injection:
  16/16 codec cases pass; zero-drop/next-success/stop-drain/late-callback and
  interrupted-notification tests pass. Baseline failures recorded in results.
- Kernel patch0004 logs per-stream missed payload/empty-transfer/error counters
  under the request lock. Codec/source summaries include error/reset/timeout
  counts and encode/OUTPUT/CAPTURE wait timing, avoiding per-frame logging.

Independent integrated and final scoped reviews found no blocking issue.
A clean application of all14 camera patches to the pinned downloaded archive
matches the compiled source exactly, including the final pipe correction.
Both integrated kernel/userspace build and final camera rebuild/repack exited0.
Final camera compile has no pipe unused-result warnings. Incremental Buildroot
emitted comm warnings about missing before-install file-list metadata; the
installed content and final rootfs were independently checked, not assumed.
Build logs: `diagnostics/build-audit-fixes.log`, `build-audit-final.log`.

Export used tar stream. All image/rootfs/kernel hashes match Docker originals.
Parsed the SD image FAT16 kernel and rootfs partition and matched exact outputs.
Compared with held mic-gating rootfs: only S60, `/usr/bin/pisight-mic`, and
`/usr/lib/libuvcgadget.so.0.4.0` changed. All overlay scripts match source, PWM
pigpio remains configured, no AppleDouble files. Kernel vmlinux includes both
`afunc_resume` and `u_audio_resume`. Verification script:
`/private/tmp/pisight-verify-audit-fixes.py`.

A brief actual packaged ARM launch/linkage check also passes using the existing
emulator in a disposable extracted filesystem: BusyBox parses S60, jq runs,
uvc-gadget prints help, settings store rejects missing arguments with2, and
supervisor loads ALSA and exits1 when its hardware card is absent. No full VM
boot was attempted; user correctly pushed back on unnecessary VM work. These
checks do not establish media performance. No physical drives were written.

Remaining evidence limits: software deadlines bound the userspace DQBUF retry
loop, not a kernel driver hanging inside STREAMOFF/close. Source function tests
stub camera and teardown dependencies, not actual DMA/concurrent hardware.
Existing ALSA format/period/latency and USB packet scheduling stay unchanged;
active microphone latency and remaining USB JPEG errors/FPS must be measured
on target. Do not infer physical recovery from these passing offline checks.
Next useful hardware test remains verified720p distinct-frame timing with mic
closed/open/closed, plus XU settings change and normal/rapid reopen/resume.

**Latest, 2026-09-27:** The pigpio PCM ownership correction restored changing
microphone samples, but **video degradation and reported mic delay remain
unresolved**. The earlier claim of native 720p/30 recovery was wrong: the probe
counted repeated images and macOS negotiated 1080p. Corrected capture verifies
720p and hashes visible pixel bytes: about 18–19 distinct fps, with other
sessions falling below 1 fps. Host USB logs also report JPEG decode failures.
Do not dismiss this as Discord or FFmpeg capture overhead.

Previous user-flashed image: `diagnostics/sdcard-uvc-recovery.img`, SHA-256
`2c5bdd75704b59c9c35189dcbfe56172555ba7a9a7d26ae35bfa91922e226a8e`.
It includes the PWM pigpio correction, UVC -ENODATA recovery, and extended
CPU/IRQ logging. Source reproduction confirms why PCM conflicted
with I2S; it does not establish the cause of remaining video/latency issues.
The agent has not written to the physical SD card in this investigation.
Readback now confirms diagnostic logging works; see the next section.

## Recovery-image target readback and microphone lifecycle fix (2026-09-27)

Read `/Volumes/NO NAME/PISIGHT.TXT` and `isight.json` without writing to the
card. Archived log: `diagnostics/target-uvc-recovery.log` (359,845 bytes), SHA-256
`01f355fcb4a22acac1137814c6e3c5912d9bb202261902735e2d3d2998c7c529`.
Raw snapshot counters: `diagnostics/recovery-target-cpu.json`. Eleven snapshots
cover uptimes 6.83–634.40 seconds. `/proc/stat` uses USER_HZ=100, not the kernel
CONFIG_HZ=1000; per-thread schedstat CPU is nanoseconds.

**Confirmed idle bridge cost:** During entirely camera/mic-closed windows
133.70–195.79 and 323.90–634.40, alsaloop uses 29.9–30.4% of the single CPU.
It runs SCHED_RR priority 99; UAC2 playback stays full at 9600 samples (200 ms),
with frozen hardware pointer and repeated capture overruns. Pigpiod uses about
7.5%, total busy CPU about 43%, USB IRQ33 about 1000/sec in these idle windows.
Mixed streaming windows reach 81–82% busy CPU and 8.1–8.5k USB IRQ/sec averaged
over whole snapshots (do not interpret these mixed-window values as exact
active-session rates). Current per-thread logs lose exited encoder workers;
UVC process totals cannot be reconstructed by summing only surviving threads.
This establishes a specific CPU/backlog defect, not the sole cause of low FPS
or physical sound-to-host latency. Active snapshot at69.29 has 7584 queued
samples (~158 ms); snapshots are too sparse to characterize latency fully.

**Settings-save root cause:** Card still has `microphone: true`. All three XU
SET attempts logged `sh: set: -eu: invalid option` followed by save failure.
BusyBox 1.37 hush does not implement `-u`; separating the flags would not help.
Changed `isight-config-store` to `set -e`, retaining explicit argument guards.
Built the same BusyBox configuration natively for Linux in an isolated source
copy: original script exits1 with the exact error; corrected script passes
syntax and rejects four invalid-input cases with exit2; errexit confirmed.
Test: `diagnostics/check-settings-shell.py BUSYBOX SCRIPT`. Full Pi persistence
still needs verification. Host USB tool no longer claims unchanged readback
proves a save. The video-only native probe now works when UAC2 is absent.

**Prepared lifecycle change:** New Buildroot package `pisight-mic` subscribes
to the existing UAC2 `Playback Rate` ALSA control before initial read. Kernel
`u_audio_rate_get` reports0 when inactive and48000 while host capture is active;
`set_active` notifies subscribers. Supervisor runs the existing alsaloop only
at48000, stops/reaps it on idle or supervisor shutdown, and retries crashed
children after1s. Control poll timeout250ms reaps failures; events wake
immediately. Bridge format, latency request, real-time scheduling and USB
descriptors remain unchanged to isolate this trial. S61 starts the supervisor;
S62 includes its thread counters. Idle bridge removal and fresh PCM opens are
expected to remove stale startup backlog, but active-session latency and USB
JPEG errors may need further work.

`diagnostics/check-mic-supervisor.py` compiles the actual supervisor against a
fake ALSA event backend and runs real child processes. Four cases pass: idle/
toggle handling (including duplicate events and unsupported rate), active at
startup, bounded crash retry, forced cleanup of a TERM-ignoring child. Target
cross-build additionally checks the real ALSA headers/library. These tests do
not simulate DMA, USB timing, physical audio delay or camera frame rate.

**HOLD — withdrawn after broader code audit; do not flash this candidate:**
`diagnostics/sdcard-mic-gating.img`, 41,390,592 bytes, SHA-256
`a53d7bb5e734366097fa6214678901a2f946c989983bb49884ae0017ed384f8f`.
Build `make -C /work/buildroot pisight-mic-rebuild all` exited0. Exported via
tar stream; checksum matches the Docker artifact. Verified image FAT16 kernel
and rootfs match build outputs; kernel is byte-identical to the recovery image.
Extracted rootfs differs only in S61, S62, isight-config-store and the new
ARM/EABI5 `/usr/bin/pisight-mic` executable. No AppleDouble files. Saved build
log: `diagnostics/build-mic-gating.log`. Supervisor lifecycle4/4, prior UVC
branch regression7/7, matching-hush settings tests, Swift probe compilation,
shell syntax and git diff checks pass. Independent read-only review found no
blocking issue; noted that an extremely brief close/reopen can coalesce before
rate read and retain the bridge (rapid-reopen freshness is unverified).

Build environment additions: host test BusyBox at
`/work/diagnostics/busybox-native-src/busybox`, built from the target BusyBox
1.37 config in a separate source copy with CROSS_COMPILE empty/ARCH=x86_64.
Do not clean the original target BusyBox source. `oldconfig`, not
`olddefconfig`, is the supported BusyBox target. The new package is enabled in
the repository Pi Zero defconfig and the persistent volume's Buildroot config.
Image verification script: `/private/tmp/pisight-verify-mic-gating.py`.
The user must flash; never write physical drives. After replug, repeat fixed
720p distinct-frame measurements and uninterrupted video/mic toggle. Test a
real change through the existing XU before relying on it for no-card A/B boots.

## Recovery-image host results (2026-09-27, 11:35–11:40)

The user flashed `sdcard-uvc-recovery.img` and reconnected. PiSight enumerated
at 480 Mb/s. Actual 720p distinct-image rates remain below 30:

- Video only: 345 distinct frames, 18.11 fps by arrival span; USB decoder 346
  completed, 1 dropped.
- Video + mic: 562 distinct images, 18.82 fps; 896 AVFoundation callbacks
  included 334 repeated images. USB decoder 588 completed, 95 dropped. Host
  audio timestamps contiguous; this does not measure audible delay.
- Video-only reopen: 344 distinct frames, 17.65 fps; USB decoder 345 completed,
  0 dropped. No sub-1-fps stall during these short trials, but not proof of
  reliable reopens/endurance.
- **Controlled uninterrupted video, microphone toggled by a separate FFmpeg
  process:** 60-second native video probe at fixed 720p, mic open for the middle
  20 seconds. Before/during/after stable windows (13.005/15.605/17.530 seconds)
  measured 17.685/21.018/15.802 distinct fps and **0/52/0 JPEG decode errors**.
  Video stayed open throughout; this removes camera restart and AVFoundation
  joint audio/video output as the explanation for mic-associated decode errors.
  Across the full session, USB decoder completed 1097 frames and dropped 68.

Results: `diagnostics/uvc-recovery-host-results.json`; host log:
`diagnostics/recovery-toggle-usb.log` (ignored local artifact). Temporary data
are in `/private/tmp/pisight-pwm-test/recovery-*`. Native probe now also records
wall times of changed frames, allowing alignment with mic activation.
The recovery patch has NOT restored frame rate. Do not declare USB fixed.
The extended Pi logger should contain CPU/interrupt/thread counters throughout
these trials; next readback should quantify scheduling and idle bridge cost.

**USB settings attempt:** Existing PiSight XU can be read on macOS using
Homebrew libusb, no interface detachment or driver reset. Control interface 0,
unit 4, GUID `PiSightSettings1`; original GET_CUR `014b000002010000` (75°,
EV 0, activity logo, mic on). `diagnostics/usb-settings.py` was added as a local
diagnostic. Two mic-off SET_CUR operations returned 8-byte transport success
but subsequent GET_CUR stayed on, including with 500 ms processing delay.
Sent mic-on to restore the original value; readback is on. This confirms only
cached GET_CUR, not file persistence. Inspect `isight.json` and daemon errors
on next card readback. Original payload saved at
`/private/tmp/pisight-pwm-test/settings-before-isolation.json`. No raw/host SD
writes were made; these were requests for PiSight to save its own settings.
Do not assume the camera-only setting change worked or request a blind reboot.

**USB scheduling candidate, not patched:** f_uvc forces bInterval=1 for
streaming_maxpacket >1024 (high-bandwidth HS endpoint). Simply changing
streaming_interval while keeping 2048 has no effect. Lower-frequency trials
would also require maxpacket<=1024 and careful payload/bandwidth validation.
Do not change this before considering the new target CPU/IRQ evidence.

## SD log readback and UVC recovery work (2026-09-27)

Read `PISIGHT.TXT` and `PISIGHT-I2S.S32` from `/Volumes/NO NAME` without
writing to the card. Local log copy: `diagnostics/target-pcm-clock.log`
(ignored); originals also copied to `/private/tmp/pisight-pwm-test/target-*`.
Checksums of card and copied files match:

- Log: `c47710b812c6ebd97916a34955b6d3a8277262da9e99b46d5f1f76f403b8008f`.
- I2S: `090adf463d5b7c64f7edcff357c7129f3095ad2bdae0e6f9ac6888b230c79fb4`.

The logger works after the PCM correction. It saved five snapshots between
uptimes 6.83 and 88.13 seconds, then stopped as programmed; later severe
reopen stalls are not captured. The first stream was 720p/30, UVC STREAMON
at 65.407807, first source frame at 66.954465 (16,268 bytes), STREAMOFF at
77.244848. It explicitly selected the bcm2835 hardware encoder `/dev/video11`.
The `00990a67` codec warning refers to H264_LEVEL, not JPEG quality.

**Confirmed USB error handling defect:** DWC2 completes missed isochronous
transfers with `-ENODATA` (-61). The target logged this at 65.963924, six times
around 66.925, and three times around 77.242. UVC's completion switch handles
only `-EXDEV` as a missed transfer, so -61 invokes `uvcg_queue_cancel(queue, 0)`:
all queued buffers are returned as errors and `buf_used` resets to zero, even
for an empty startup request. Patch
`webcampi/board/raspberrypizero/linux-patches/0002-uvc-recover-dwc2-missed-isoc-transfer.patch`
routes -ENODATA to the existing -EXDEV recovery. It does not prevent missed
transfers or prove all degradation is fixed. Test
`diagnostics/check-uvc-missed-transfer.py` extracts the actual completion status
switch and executes it against mocked request/queue structures. Before patch:
2/7 fail (both -61 cases); after: 7/7 pass, including shutdown and fatal errors.
Physical USB timing and complete driver concurrency are not simulated.

**Audio:** In every saved snapshot, gadget playback was RUNNING but its hardware
pointer remained 0, application pointer 9600, delay 9600 samples (200 ms at
48 kHz). The bridge repeatedly logged capture overruns. The source capture
continued/restarted while the Mac had not opened mic capture. This confirms the
idle-host backlog/overrun condition on hardware, but the log has no per-process
CPU counters and no active mic session, so it does not prove the complete
video-starvation or subjective audio-latency explanation. Raw I2S capture
succeeded: 96,000 stereo S32 frames, left channel 80,877 distinct values, right
channel identically zero, consistent with a left-slot mic. Keep these data
local; there is no need to send or publish the audio recording.

**User flashed and reconnected this image; testing still shows degradation:**
`diagnostics/sdcard-uvc-recovery.img`, 41,386,496 bytes, SHA-256
`2c5bdd75704b59c9c35189dcbfe56172555ba7a9a7d26ae35bfa91922e226a8e`.
Kernel rebuild and final image repack exited 0. Verified exported checksum
against the Docker build artifact; parsed the image's FAT16 kernel and rootfs
partitions and matched both to build outputs. Extracted rootfs comparison
against the PCM-corrected image found only `etc/init.d/S62pisight-diagnostic`
changed. The image retains PWM pigpio defaults. The compiled kernel has the
-ENODATA recovery case. Branch regression 7/7, shell syntax and diff checks pass.
An initial packaging check caught an AppleDouble `._S62pisight-diagnostic`
file; it was removed from overlay and target before the final repack. Use
`COPYFILE_DISABLE=1` on future macOS tar exports to prevent this. Build logs:
`diagnostics/build-uvc-recovery.log`, `build-uvc-recovery-repack.log` (ignored).
Only the user should flash the card; the agent made no physical-drive writes.

The recovery image also changes the diagnostic logger to snapshot every
60 seconds for 30 minutes, including ALSA hw_params, CPU/interrupt totals,
per-thread CPU/scheduling counters, and memory state. It copies the raw I2S
sample once per boot. The audio bridge is unchanged to keep this video-recovery
trial distinct from an audio-bridge lifetime change.

## Hardware results after the PCM clock correction (2026-09-27)

- USB ID `0525:dead` enumerates at 480 Mb/s as `iSight` camera and
  `Capture Inactive` microphone. Select devices by name, never numeric index.
- **Original native test is invalid as a camera-fps result.** It counted 446
  callbacks over 14.877 seconds (29.911 fps), but did not hash images or verify
  the active mode after `startRunning()`. The corresponding 11:06:58–11:07:13
  USB session negotiated 1920×1080 MJPEG and reported only 264 delivered frames
  plus decode failures. Audio timestamps were contiguous; that does not measure
  physical sound-to-host delay.
- A subsequent 11:10:45–11:11:03 USB session negotiated 720p but delivered only
  **11 frames in about 18 seconds**, with JPEG decode failures. This supports
  the user's report of severe degradation.
- Enhanced native probe at 11:17:45 counted 597 video callbacks but only
  **334 distinct images (~17.08 fps)** at actual 1080p; 263 consecutive repeats.
  Matching USB session reported 409 decode submissions, 341 completions and
  68 drops. A reopen at 11:18:48 produced **8 distinct images (~0.70 fps)**,
  despite 241 callbacks. Neither run was actually 720p.
- Fixing the probe's output dictionary to include pixel width AND height
  finally kept the active mode and delivered buffers at 1280×720. At 11:19:27,
  host audio capture enabled: 430 callbacks, **277 distinct images, 18.86 fps**.
  At 11:19:57, host audio capture closed: **363 distinct images, 18.32 fps**.
  The Pi audio bridge keeps running in both cases, so this does not isolate
  bridge CPU starvation from other camera/USB costs.
- Earlier FFmpeg frame-hash captures measured 17–18 distinct fps. The native
  duplicate-frame discovery means those results cannot be dismissed as an
  FFmpeg-only performance artifact. FFmpeg audio captures also had chunk gaps;
  native host audio delivery was contiguous, but end-to-end audio delay remains
  unmeasured. The user has not yet specified the app/test path or delay length.
- A named Pi mic recording has 6,524 distinct S16 values, range -5011 to 12517,
  mean -22.22, RMS 784.92, no clipping, unlike the previous constant -32280.
  Recording: `/private/tmp/pisight-pwm-test/microphone.wav`.
- Probe: `diagnostics/native-capture-timing.swift`; results and corrections:
  `diagnostics/pcm-clock-host-results.json`. Compile with `swiftc -O` and run
  outside the filesystem sandbox for media access. Optional duration argument,
  `--video-only`, and `PISIGHT_RESULT` output path. Default output directory
  `/private/tmp/pisight-pwm-test` must exist. Hashes exclude packed-pixel row
  padding. No images/audio are stored by this probe.
- Host logs are `/private/tmp/pisight-pwm-test/uvc-degradation.log` and
  `uvc-degradation-final.log`; preserve relevant summaries above if tmp is lost.
  High invalid-packet counts alone are inconclusive (idle UVC packets can be
  counted invalid). Decode errors and distinct frame counts are stronger data.

## Remaining investigation

- Inspect the current card's `PISIGHT.TXT` after these sessions if it saved.
  Readback completed; see the SD log section above. The first stream used hardware
  encoding and logged both USB -61 errors and idle microphone overruns.
  There is no SSH/serial access to this image. Avoid a speculative new flash
  before retrieving this existing evidence if available.
- Source inspection confirms `alsaloop` still starts at boot and runs SCHED_RR
  priority 99 even while the host is not recording. UAC2 playback advances its
  ALSA pointer only on USB completions. Prior mock evidence of frozen-playback
  CPU spinning remains a candidate, not proof of the full target failure.
- UAC2 auto high-speed interval chooses bInterval 4 for mono 48k/S16 (1 ms).
  Its default queue has 2 requests; UVC uses 2048-byte payloads every microframe.
  Do not infer raw bandwidth exhaustion from this; measured compressed frames
  are typically only tens of kB. Target scheduling/transfer evidence is needed.
- Inspected stream restart and hardware encode source; no confirmed new cause.
  `libcamera_source_stream_off` stops camera, clears requests and completed
  queue, deletes encoder; encoder destruction drains work before source buffers
  are freed. There are unchecked startup/queue errors and unsynchronized request
  queue access, but neither is demonstrated to explain these measurements.

## Historical result before the PCM correction (superseded above)

- macOS now enumerates an **iSight camera** and an audio input named **Capture Inactive**. Discord can select/start that input, but the user hears/records no microphone signal.
- The camera initially gave a black QuickTime preview. In a later Discord attempt, video **did start**, but startup took a long time and the frame rate was extremely low. We do not yet know whether both attempts used the same flashed image, or whether the later attempt used the diagnostic image.
- The rear logo LED flashes briefly at boot and turns off. This is not evidence of UVC streaming: the daemon's GPIO initialization turns it on and the configured `activity` logo mode turns it off a second later.
- A prior SD card/image, from before the microphone/settings work, is reported to work as a camera. We have not measured its frame rate against this build.

## Verified failures already fixed

1. The first new image had only macOS audio devices named **Playback Inactive** and **Capture Inactive**, and no camera. Its boot log showed the built-in `g_audio` driver bound the Pi Zero's only USB controller before ConfigFS UVC could bind (`Device or resource busy`). Commit `5607c37` in `webcampi` disables the legacy USB audio and MIDI gadget drivers.
2. The next image advertised a Mac audio output rather than an input because the UAC2 ConfigFS channel masks were reversed. Commit `1a5d06e` sets `p_chmask=1`, `c_chmask=0`; the Mac now sees an audio input. Enumeration does not prove that the I2S-to-UAC2 audio bridge works.

The current normal image is `webcampi/buildroot/output/images/sdcard.img` (SHA-256 `e9d89da16f7150d1bb7da683c9048210263992544cab0065718be14a7a431fbf`). The original working hardware MJPEG path is the baseline for comparison. Recent changes include the I2S overlay, UAC2 gadget function, UVC settings/controls, and another advertised resolution.

## One-off diagnostic image and caveat

`webcampi/buildroot/output/images/diagnostic/sdcard-video-diagnostic.img` (SHA-256 `775a0e63a30edf2f28e3e82c0ab0f8acf54b4e6592df5c0737938dd2f2623dfe`) is a repack of the normal root filesystem with extra logging. It leaves the normal image untouched. Build script: `/tmp/pisight-video-diag-build.sh`; its last staging directory is recorded in `/tmp/pisight-video-diag-stage-path`.

The diagnostic boot script captures setup output, UVC events and daemon output, process/ALSA state, mic bridge log, and kernel log to `/boot/PISIGHT.TXT`. **Its logger waits for `EVENT_STREAMON`, daemon death, or a 600-second timeout before writing the file.** The user's first look found no `PISIGHT.TXT`; that alone is inconclusive. Even after video starts, an absent file could mean no logged `STREAMON`, failed mount/write, wrong image, or logger failure. Do not infer a video root cause from absence of the file. If it remains absent, make the next diagnostic write an unconditional boot snapshot and update it after a preview attempt. Avoid another flash if the current card yielded the file after the later Discord test.

## Code paths and open questions

- UVC startup: `webcampi/package/uvc-gadget/S60uvc-gadget` applies `/boot/isight.json`, runs `uvc-gadget.sh`, then starts `/usr/bin/uvc-gadget`. The hardware MJPEG encoder is in `package/uvc-gadget/0003-add-bcm2835-hardware-mjpeg-encoder.patch`; UVC event logging is in patch `0005-uvc-add-event-diagnostic-logging.patch`. Check actual `PROBE`, `COMMIT`, `STREAMON`, `FIRST_FRAME`, and daemon errors before attributing the slow video to USB bandwidth or audio.
- Microphone bridge: `board/raspberrypizero/rootfs-overlay/etc/init.d/S61pisight-mic` waits for ALSA cards `PiSightMic` and `UAC2Gadget`, then runs `alsaloop -C pisight_mic -P hw:CARD=UAC2Gadget,DEV=0 -f S16_LE -c 1 -r 48000 -t 50000 -n`, logging to `/tmp/pisight-mic.log`. `asound.conf` defines `pisight_mic` as a route from the I2S capture card's left channel. The device-tree overlay is `board/raspberrypizero/pisight-ics43434.dtso`. Determine whether the bridge starts, whether PCM reads nonzero samples, and whether UAC2 transmits them.
- The Mac's **Capture Inactive** label is the kernel UAC2 function's idle alternate-setting string, not a reliable health indicator. Cosmetic renaming can follow a working mic/video path.
- `uvc_stream_enable` and `uvc_stream_start_encoded` have unchecked return paths; a failed source or V4L2 `STREAMON` can be hidden. Verify from logs before changing this.

The user is tired of flashing and wants evidence-led fixes. Preserve the unrelated staged `.idea` files in the parent repo. The `webcampi` submodule is clean at this handoff; no diagnostic source changes are committed.

## Astra independent review

Astra found a reproducible **host-not-recording audio-loop scheduling problem**, but did not claim it explains every symptom. The bundled `alsaloop` 1.2.13 requests `SCHED_RR` priority 99. It starts at boot even before the host opens microphone capture. In a controlled mock-PCM trial using the exact bundled source, five seconds of clocked playback used 0.003 CPU seconds; five seconds of frozen playback used 1.399 CPU seconds (~28%) and repeatedly overran capture. The mock models ALSA pacing, not the Pi DMA/USB/video hardware. This is a plausible cause of video startup delays on the single-core Zero, but the slow video seen after Discord opened the mic and the silent mic remain unexplained.

Astra separately verified that the production left-channel ALSA route can convert stereo S32_LE input to mono S16_LE: a 48,000-sample mock produced 48,000 correct nonzero left-channel samples. That test does not prove the physical mic is wired, receiving clocks, or reaching the gadget. The bridge startup script prints `OK` before `alsaloop` succeeds and does not supervise it; the input can remain enumerated if the bridge dies.

The reproduction details and source anchors are in `/tmp/pisight-alsa-repro/README.md` (local temporary artifact). No production source or image was modified. The highest-value **no-reflash** test, if the Pi can plug into the Linux machine that runs this repository, is to measure fixed-mode 1280×720 MJPEG frame delivery with the USB microphone closed, actively recording raw PCM, then closed again. Inspect raw sample levels separately from Discord. Collect `PISIGHT.TXT` if it appeared after the later stream; its absence alone remains inconclusive. Only patch bridge lifetime/scheduling after target evidence confirms its role.

## macOS host measurements after handoff (2026-09-26)

- The connected PiSight enumerated at USB ID `0525:dead`, 480 Mb/s, with `iSight` video and `Capture Inactive` audio. AVFoundation's numeric camera indexes changed between runs. Two apparent 30 fps results were actually from a separate Anker H264 camera. Select `iSight` by **name** in subsequent captures.
- macOS negotiated PiSight's 1280×720 MJPEG mode with a 30 fps frame interval. In PiSight sessions, the host saw about one usable frame per second or none; one capture started six seconds late and delivered 14 frames over about 24 seconds. A named `iSight:none` FFmpeg capture produced only six frames before its 15-second safety timeout. macOS UVC logs counted 156,552 USB packets and 14 frames in one slow session, with 156,287 packets marked invalid. A working Anker session also had many packets marked invalid, so that counter alone does not explain the PiSight failure.
- Raw 48 kHz mono capture from `Capture Inactive` produced constant sample value `-32280` (`0x81e8`) for all 213,376 samples in a five-second run while PiSight video was open. An earlier capture was almost entirely the same value with a short span of zeros. This confirms unusable USB PCM at the host, before Discord's processing. It does not yet locate the defect between the I2S mic, ALSA bridge, and UAC2 gadget.
- PiSight video was already near one frame per second before opening host microphone capture and remained slow while capture was open. This does not confirm the prior `alsaloop` scheduling hypothesis as the sole video cause.
- The one-off diagnostic image and `/tmp` artifacts from the prior host are absent on this Mac. Inspect the current card's `/boot/PISIGHT.TXT`, if present, before changing the target image. The target daemon log should say whether it selected `bcm2835` hardware MJPEG or fell back to `libjpeg`.
- The card's `isight.json` had `"microphone": true` and no `PISIGHT.TXT`. We changed only that boolean to `false` on the FAT partition and safely ejected the card. After reboot, the Mac still saw the UAC2 input, so this did **not** produce a valid microphone-off comparison. The setting may not have been applied, or the running image may differ from the source. The next image logs the config-apply trace, applied environment, and gadget setup to distinguish these cases.
- A fresh diagnostic Buildroot image was built from this checkout. Its one-off init scripts capture raw I2S PCM before the audio bridge starts and copy boot, UVC, ALSA, and kernel snapshots to `PISIGHT.TXT` on the FAT partition every 20 seconds during the first five minutes, plus after `EVENT_STREAMON`. Do not treat these as runtime findings until the image is flashed and the files are collected.

## Current diagnostic image (built 2026-09-27; user flashed it)

- Verified image: `diagnostics/sdcard-diagnostic.img`, 41,382,400 bytes, SHA-256 `842bde04e8bc369b2f893edeb80495047b719a3fb4d100ae498dadb02c6c83e0`. The full Buildroot build exited successfully. Its log is `diagnostics/build-amd64.log`.
- Build host: Docker Desktop on the ARM Mac, running x86-64 Ubuntu 24.04 on a Docker-managed Linux volume. The project's pinned Bootlin ARMv6 cross-compiler is only selectable on an x86-64 Linux host; a native ARM64 Linux attempt reached an unavailable custom toolchain. Building on the Mac-shared filesystem also caused a host CMake archive failure. The Linux volume resolved it.
- The three diagnostic init scripts in `diagnostics/` were staged into `webcampi/board/raspberrypizero/rootfs-overlay/etc/init.d/` before the build. Verified their exact bytes and executable modes inside the generated SquashFS, along with `/usr/bin/arecord`. Verified the FAT boot partition has `zImage`, Pi Zero DTB, firmware, and the microphone overlay (inside `overlays/`).
- Direct file copies from the Docker volume to a Mac bind mount silently zeroed bytes starting at offset 8192. The verified image was exported through a Docker tar stream, and its macOS SHA-256 matches the Linux build artifact. Do not use the discarded direct-copy artifacts.
- The user flashed the image and connected the Pi on 2026-09-27. After connection and replugging, macOS `ioreg -p IOUSB` and `system_profiler SPUSBHostDataType` showed no PiSight device at all (expected `0525:dead`). No video or microphone capture was possible. The user confirmed the cable/setup had worked previously, so do not keep suggesting the cable as the primary explanation. macOS kernel logs at 10:24:39–10:25:00 and 10:27:26–10:28:00 show repeated `AppleUSBHostPort::createDevice: failed to create device (0xe00002bc)` and `failed to address device` on hub port `00133000`, ending in `persistent enumeration failures`; there were similar failures on `00143000` at 10:29. This suggests the host detects an attach but fails before identifying USB descriptors. It does not yet establish whether the cause is image boot, gadget startup, Pi power, or hardware.
- The built image was rechecked: its SHA-256 matches the Docker build artifact; its embedded 32 MiB FAT partition matches `boot.vfat` byte for byte; the FAT root contains `bootcode.bin`, `start.elf`, `fixup.dat`, Pi Zero DTB, `config.txt`, `cmdline.txt`, overlays, and an ARM zImage. The built kernel enables MMC, SquashFS LZ4, DWC2 peripheral mode, ConfigFS UVC/UAC2; legacy `g_audio` is absent. The diagnostic `S60uvc-gadget` differs from the branch version only by redirecting config/setup output to `/tmp` logs. No definite boot/gadget regression has been found in static inspection. The card has not been read back, and its actual flashed bytes are unverified. `config.txt` disables the green ACT LED, so its state cannot diagnose boot. If the gadget reappears, capture by device name and inspect `PISIGHT.TXT` and `PISIGHT-I2S.S32` before proposing an encoder or mic fix. The user explicitly does not want us writing to any physical drive.

## Read-only SD inspection after failed enumeration (2026-09-27)

- The card mounted as `/Volumes/NO NAME`. There is no `PISIGHT.TXT`, but there **is** a hidden, zero-byte `.PISIGHT.TXT.tmp`, plus a newly seeded `isight.json` with `"microphone": true`. Unlike an entirely missing log, the temporary file establishes that Linux reached the diagnostic logger's copy step. A complete boot failure is no longer a useful leading hypothesis. It does not identify why the copy failed or stalled.
- The boot partition has 23 MiB free. The kernel, Pi Zero DTB, and config.txt hashes match the new image. A read-only image of the flashed root partition exactly matches the diagnostic image's root partition: SHA-256 `214e4d52afaebe8406a180fa14abadad4b7fd6eac92524a17c5f4c2b4e7ffa77`. This confirms the diagnostic scripts are actually on this card. These checks supersede the previous uncertainty about flashed bytes.
- Read-only copies are `/private/tmp/pisight-fat-readback-20260927.cdr` and `/private/tmp/pisight-rootfs-readback-20260927.cdr`. The temporary log's FAT directory entry has cluster zero and size zero; no diagnostic text was found in a scan of the copied FAT partition. There is no report data to recover from that file.
- Prepared `diagnostics/isight-microphone-off.json`, differing from the mounted card's config only by `"microphone": true` becoming `false`, for a single no-reflash isolation test. It has **not** been applied to the card. This disables UAC2 and the audio bridge but leaves the raw I2S probe enabled. Recovered enumeration/logging would implicate the USB audio/bridge path, not establish a specific audio root cause. Original config saved at `/private/tmp/pisight-isight-original-20260927.json`. Inspection has made no writes to the SD card.

The unproven endpoint patch is quarantined at `diagnostics/held-patches/0015-gadget-usb-video-timing-trial.patch` so normal builds do not silently include it.
