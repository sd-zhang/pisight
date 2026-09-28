# Camera CPU investigation: suppressed debug formatting

Hardware patch0009 still uses approximately95% CPU during simultaneous capture.
The audio bridge accounts for about4%; pigpiod about11%. CameraManager and the
inferred IPA thread account for about23% and24% of scheduled runtime, with
substantial run-queue waits. See `capture-audio-arm-20260927/thread-costs.json`.
Interrupt time overlaps task attribution on this kernel; these are not a
strict additive CPU budget. This does not establish an inherent Pi CPU limit.

## Confirmed unnecessary work

Exact libcamera v0.5.0 source expands LOG into `_log(...).stream()`. Construction
creates a timestamp and formatted source location; Loggable also builds an
object prefix. Stream insertions evaluate their operands. The destructor only
then checks severity against the category threshold. Thus defaultINFO still
formats discardedDEBUG messages. AWB coarse/fine searches contain such logs
inside their loops; camera management and per-frame IPA algorithms also use them.
Compiler flags are-O3 and the toolchain isARMv6hard-float: this is not an-O0 or
soft-float diagnosis.

`libcamera-log-probe.cpp` links the actual builtARMlibcamera-base and runs under
qemu-arm-static withCPUarm1176. This is a focused software reproduction, not a
VM model of USB/camera hardware. Baseline20000suppressedmessages performed20000
formatter calls and producednooutput; a suppressed member log built1prefix.
A suppressed throwing operand also executed. This establishes unwanted work
without reflashing the Pi. See `libcamera-log-cost-baseline.txt`.

## Correction

The header guard checks severity before constructing the message or evaluating
stream operands. A voidify expression preserves insertion chaining and if/else
use, including namespace-qualified LOG calls and member_log/prefix dispatch.
Fatal always passes the earlyguard. The existing destructor/output logic remains.
LOG now yieldsvoid; its internal docs reflect statement-style lazy behavior.
Source audit found no current callers relying on the old stream return type or
obviousrequired operand side effects. No existing ABI layouts/signatures changed.

Guarded probe:0formattercalls,0suppressedprefixes. Visible messages, stream
manipulators, runtime debug enable/disable, defaultcategory, qualified/membercalls,
and elsebinding pass. Fullbuild caught qualifiedLOG inside staticderived methods:
the qualification applied to the new guard, leaving backend lookup to find the
inherited member. A focused reproducer fails, then passes with function-local
`using libcamera::_log;`. The two affected functions (V4L2Device::fromColorSpace,
CameraSensorRaw::match) now explicitly select that free backend. Instance logging
retains memberprefixes. QualifiedLOG in staticderived methods needs this explicit
selection; the new macro is not universally sourcecompatible with old expressions.
The initial failed build is preserved in build-camera-log-guard-first.log.
Suppressed exceptions are skipped. Fatal withcategory
threshold100 andASSERT(false) both abort in isolated subprocesses(exit134);
core dumps disabled. Independent review requested these extra cases and docs;
all addressed. ExistingASSERT(true) continues.

Isolated emulated elapsed for20000messages:0.200720sbaseline,0.000382sguarded.
These numbers are not Pi timings and must not be converted to totalCPU/FPSgain.

## Packaging status

Patch: `webcampi/board/raspberrypizero/patches/libcamera/0001-skip-suppressed-log-formatting.patch`.
ExistingBR2_GLOBAL_PATCH_DIR installs it for fresh builds. Fullcamera/IPA rebuild
is required because each compiled LOG site contains the macro. Final ARM build
exited0 (`build-camera-log-guard.log`) with no compiler errors/warnings and eight
existing Buildroot inventory comm notices. Source snapshots `/private/tmp/pisight-log-cost`.
All four compiled source hashes match; clean patch application exact. The rebuilt
IPA module signature verifies. Logging probe passes against the rebuilt library.

Verified final image `sdcard-camera-cpu-fix.img`,41419264bytes, SHA256
`51899753b7252a0d74215050b02f3d15bd4b4fc5f84f3a0c7b551a217e168c19`.
Only five rootfs artifacts changed from the rename image: libcamera-base,
libcamera, IPA module, IPA signature, IPA proxy helper. Boot/kernel unchanged.
See camera-cpu-image-verification.txt and camera-log-ipa-signature.txt.
Final image combines shutter removal and exactiSightMicrophonename in both modes.
No request to reflash merely to continue investigation; no physicaldrivewrites.

The remaining unknown is how much targetCPU and simultaneousFPS this saves.
Existing evidence proves wastedwork, not that it explains all remaining losses.
Acoustic latency remains unmeasured. No serial access added or used.
