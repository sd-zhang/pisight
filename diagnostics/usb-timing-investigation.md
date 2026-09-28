# Simultaneous video/audio investigation — 2026-09-27

Acceptance requires simultaneous smooth video and low-delay microphone audio.
Mic-off runs are diagnostic controls, not an acceptable product workaround.

## Evidence from the flashed audit image

Read-only card archive: `target-audit-fixes.log`, 138372 bytes, SHA256
`280d99ab778251f4bf5672b39875351cfc6e9220bdae636c0b9213d9e3ea3430`.
Original and copied hashes match. Summaries: `audit-target-streams.json`,
`audit-target-cpu.json`, and `audit-fixes-host-results.json`.

| Stream | Encoded | Source submitted | Missed payload requests | Missed empty requests |
| --- | ---: | ---: | ---: | ---: |
| 60.267 s toggle test | 1505 | 1504 | 103 | 94 |
| 20.407 s combined reopen | 469 | 468 | 79 | 16547 |
| 6.493 s later user session | 133 | 133 | 19 | 17 |

All three report zero encoder failures, corrupt/invalid buffers, timeouts,
resets, or source drops. Encode mean is 13.24 / 13.34 / 13.67 ms, maximum
25.64 / 39.51 / 21.62 ms. These checks validate lengths/flags/JPEG markers,
not a full decode of every encoded image. They also exclude waiting elsewhere
in the camera/ISP/USB buffer-recycling pipeline.

The first source's 1504 submitted frames match 1504 host decoder submissions;
the host completed 1424 and dropped 80. Stable-window decoder errors were
0 before microphone capture, 56 during, 1 after. Missed payload requests
and damaged JPEGs are strong evidence of a transport problem after encoding;
they are not a one-to-one count because a JPEG spans multiple USB requests.
Source production also averages only ~25 fps over this stream. Do not attribute
all missing frames to the JPEG decoder or claim the camera pipeline meets30fps.

The bridge log records three starts and three stops. Every periodic PCM
snapshot is closed, and no alsaloop remains in those snapshots. Thus idle
gating works; no active PCM snapshot was captured. Supervisor CPU is about
0.04–0.055% across the snapshot windows. CPU busy percentages and USB IRQ rates
are mixed active/idle window averages, not measurements of interrupt latency.
Neither these data nor continuous host audio timestamps measure acoustic delay.

## Driver trace and hypothesis

The actual built gadget script sets `streaming_maxpacket=2048`, and the host
confirms `epPacketSize 2048`, `bInterval 1`. Kernel `f_uvc.c` forces interval1
when max_packet_mult>1, per the high-bandwidth endpoint constraint. Therefore
changing only `streaming_interval` cannot reduce the service cadence.

`uvc_video_complete()` continually replaces completed requests with ready
payloads or zero-length requests. Consequently the video endpoint continues
to require service between camera frames. DWC2's non-descriptor-DMA path
tracks target microframes in software and completes expired requests with
`-ENODATA`. UVC now recovers rather than cancelling the whole queue, but
recovery cannot deliver bytes whose transfer interval was missed.

See the upstream explanation of the DWC2 deadline handling:
https://lkml.iu.edu/2109.3/02936.html

The leading hypothesis is that this endpoint configuration imposes excessive
short-deadline service work when audio and camera processing share the original
Pi Zero. Actual payload averages ~42.5kB/frame, far below the endpoint's
16.288MB/s theoretical UVC payload capacity. The logs establish missed transfers,
not their exact triggering interrupt, DMA mode, or CPU-frequency history.
Do not call CPU saturation, interrupt latency, or cable failure proven.

## Bounded hardware experiment

Patch `0015-gadget-usb-video-timing-trial.patch` changes only the setup script:
1024 bytes, interval2. The real kernel descriptor mapping produces one packet
every250us, 4000 service opportunities/sec, and conservative payload capacity
4.048MB/s after12-byte headers (~134.9kB per30fps frame). It preserves all
advertised resolutions, frame rate, JPEG quality, microphone settings, and
kernel behavior. High-detail/larger-mode peak bandwidth remains unvalidated.

This necessarily changes transaction count as well as cadence. A positive
hardware result supports the configuration; it would not isolate cadence from
transaction count. A clean future comparison at1024/interval1 could distinguish
those effects if necessary. Do not bundle other performance changes into this
trial.

`check-usb-video-timing.py` executes the actual endpoint setup in a temporary
directory and compiles/exercises the actual built `f_uvc.c` descriptor-mapping
block. Baseline fails the intended250us assertion; patched passes, including
under the matching BusyBox hush. It also confirms2048/interval2 is forced back
to interval1. This checks configuration, not hardware behavior.

Independent review found no blocking endpoint/probe issue: userspace obtains
maxpacket from configfs, reports1024 in PROBE/COMMIT, and DWC2 handles interval>1.

Next hardware validation: fixed720p with both streams active for at least120s
to include an active periodic target snapshot, plus the same uninterrupted
mic-toggle comparison. Check distinct images, JPEG failures, audio continuity,
target missed-transfer counts, active ALSA backlog and perceived/physical delay.
Do not call this fixed based on a video-only run or configuration test.

## Built artifact

`sdcard-usb-timing-trial.img`, 41394688 bytes, SHA256
`2f6316aeac6450133bece3817a8adabf6584bf347ac6581ce61bded3365ea4fd`.
Build/repack exits0. Exact exported hashes match the build volume. Parsed image
partitions match the built kernel and squashfs. Rootfs inventory differs only
at `usr/local/bin/uvc-gadget.sh`, matching the tested script; kernel, encoder,
mic supervisor and all other regular files/symlinks are unchanged. The build
has existing incremental .files-list.before comm warnings; independent content
verification covers the resulting artifact. No physical drives were written.

The unproven endpoint patch is quarantined at `diagnostics/held-patches/0015-gadget-usb-video-timing-trial.patch` so normal builds do not silently include it.

## Offline wraparound lead — not a target diagnosis

The second target stream's16547 missed empty requests equals16384+163. The
DWC2 high-speed frame counter wraps modulo16384. This numerical resemblance
is a lead only; the recorded largest changed-image gap was0.297s, and the log
has no frame-counter or interrupt trace establishing an actual wrap failure.

`dwc2-wrap-probe.c` contains the exact local kernel increment/elapsed helpers
with minimal structs. Given an injected target0 / overrun=true / current0x3ff9
state, the target is correctly considered future. One increment clears overrun,
after which the still-future target is incorrectly considered elapsed. This
reproduces at intervals1,2,4,8. It is a conditional helper-level demonstration;
reaching this state in the current interrupt flow is NOT established. Do not
present it as the Pi's root cause or ship a kernel change based on it alone.

Relevant upstream discussion (2018):
https://www.spinics.net/lists/linux-usb/msg174128.html
The2021 elapsed-frame fix7ad4a0b1 already exists in our source; it resets request
actual/frame_number and does not justify blindly applying an old patch.

The held timing patch has been reversed in the Docker source/target as well.
The Docker output image remains the held trial until a new pack; do not confuse
output/images/sdcard.img with the source/target configuration after reversal.

Independent reachability review: normal IN completion increments once; recovery
loops stop at future targets; incomplete-IN tests elapsed before disabling.
The injected helper state bypasses those safeguards. Coalesced XFERCOMPL plus
EPDISBLD and callbacks refilling an emptied endpoint queue are possible leads,
not captured events. Current source includes the substantial2021 flow rewrite
91bb163e1e4f. No historical helper patch should be transplanted on this evidence.
