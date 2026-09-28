# Remaining CPU audit — 2026-09-28

User asks for more CPU headroom before restoring USB management. No production
changes or new image made. Current combined image full active CPU68.409%; earlier
sustained windows66–67%. This is ARM CPU utilization, not hardware encoder load.

## Measured costs

Recomputed combined-image thread costs from saved uptime68.18–132.60 snapshots:
`capture-audio-sof-shutter-20260928/thread-costs.json`. Busiest uvc-gadget threads
18.754% and14.761% runtime; another6.785%, main3.351%. ALSA4.622%, supervisor0.171%,
pigpiod0.0021%. Thread roles require stacks to identify conclusively. USB handler
elapsed13.152%,8733IRQ/s,7994video completions/s,999audio completions/s. These IRQ
and thread percentages overlap on this kernel; do not add as disjoint costs.

## Concrete source findings

1. Camera controls: current libcamera-source.cpp re-applies unchanged ScalerCrop
   and ExposureValue on every request. IPA redoes control lookup/conversion,
   including pow(2,EV). Candidate event-based control submission could preserve
   behavior if correctly handling startup/reconfigure, outstanding requests and
   change ordering. Cost unmeasured; likely smaller than full camera processing.
2. VC4 IPA applyLS resamples three lens-shading grids every processed frame;
   resampleTable recomputes coordinate geometry for each grid. Potential to cache
   geometry or unchanged outputs, but shading values interpolate each frame and
   must not simply be frozen. No hotspot samples yet. Preserve numeric output.
3. RPi IPA already has temporal decimation infrastructure, with controller minimum
   duration1/30s. Testing15Hz control updates with30fps output could lower load,
   but changes focus/exposure/white-balance response and frame-based convergence.
   It is a quality/response tradeoff, not free cleanup or a proven performance gain.
4. Raw YUV copy into hardware encoder is already removed via DMA-BUF. Compressed
   JPEG copy remains in hw_mjpeg_encoder.cpp; kernel UVC also packetizes/copies.
   Removing it is a buffer-ownership change and savings are unmeasured. Do not
   claim zero-copy is an untouched easy large gain.
5. Diagnostic timing adds work per IRQ/arm. Part of supposedly diagnostic state
   now guards recovery (previous time/frame, epoch and request serial). It cannot
   all be disabled safely. Measured DSTS probe span is only~0.274% in active window,
   not total instrumentation cost. Keep useful diagnostics per user preference.
6.8kvideo completions/s persist between frames because current UVC queues empty
   requests. Reducing them means USB scheduling/driver changes. This is a possible
   substantial structural saving but risks the reliability just restored.
7. LED/shutter idle overhead negligible. Audio bridge only4–5%, so wholesale
   replacement has a small upper bound even before accounting necessary work.
8. Build uses ARM1176 hard-float toolchain and optimized Meson release; no evidence
   this is an accidental unoptimized/debug or soft-float build.

## Recommended order

Investigate camera-side redundant work first, preserving30fps, autofocus, exposure,
colour, and USB timing. Obtain function-level timing or a faithful focused workload
before predicting gains. Profile/correct independent redundancies; avoid speculative
image churn. Controller decimation is a separate tradeoff option. USB interrupt
reduction last. No justified target such as40% CPU yet. No reflash requested.

Sources inspected: cached exact-version libcamera0.5.0 under
/private/tmp/pisight-libcamera-cpu-source/src/ipa/rpi/{common/ipa_base.cpp,vc4/vc4.cpp},
controller/rpi/{agc,agc_channel,alsc,awb,af}.cpp; current gadget source under
/private/tmp/pisight-shutter-switch/new/lib; kernel0011 snapshot under
/private/tmp/pisight-audio-sof/new/drivers/usb/dwc2/gadget.c; repository config,
DMA-BUF and recovery patches. No debugger/runtime stack evidence was obtained.
