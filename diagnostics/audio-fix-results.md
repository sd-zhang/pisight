# UAC2 activity and microphone supervisor corrections (2026-09-27)

The new `0003-uac2-resume-activity.patch` restores ALSA Playback Rate activity
after UAC2 resume from each endpoint's existing enabled state. It does not
restart an endpoint or queue another USB request. The endpoint flag now becomes
true only after `usb_ep_enable` succeeds. The function's resume callback is
registered alongside its existing suspend callback.

`pisight-mic` now refreshes a live bridge for a relevant Playback Rate value
notification, even when the final rate still reads 48000. This covers a
close/reopen pair whose notifications coalesce before the rate read. Events
for other controls and non-value events do not refresh it. Pending startup
notifications are drained before the initial rate read and child start.

Verification run locally:

```text
python3 diagnostics/check-mic-supervisor.py
PASS: idle and toggles
PASS: already active at boot
PASS: queued event at boot
PASS: bounded crash retry
PASS: unresponsive child cleanup

patch -d /private/tmp/pisight-uac2-apply -p1 --batch < webcampi/board/raspberrypizero/linux-patches/0003-uac2-resume-activity.patch
# cleanly patched the pinned u_audio.h, u_audio.c, f_uac2.c snapshot

python3 diagnostics/check-uac2-resume.py /private/tmp/pisight-uac2-apply/drivers/usb/gadget/function
PASS: inactive, active, duplicate resume and independent endpoints
```

The kernel regression compiles and executes the patched production
`set_active`, `u_audio_suspend`, `u_audio_resume`, `afunc_suspend`, and
`afunc_resume` functions with stubbed notification and endpoint state. It also
checks the production callback registration and header declaration. The test
failed against the unpatched source because its resume declaration was absent.
The supervisor regression compiles the production supervisor against a fake
ALSA event source and runs real child processes. The coalesced and queued
startup cases failed before their respective corrections.

These are source-level and host-process tests. They do not establish target
USB resume behavior, physical microphone latency, or video frame rate. ALSA
rate events contain no historical values: a notification arriving in the
narrow interval after startup drain but before the first read can cause one
extra bridge refresh. A relevant active notification also causes a bounded
refresh even if it represents a duplicate event, because it could be a
coalesced close/reopen. The bridge's ALSA format, latency request, and
scheduling were not changed.
