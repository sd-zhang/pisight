# Transport and active microphone diagnostics

This change gathers missing evidence; it is not a performance fix. The
1024-byte/250-us USB timing trial remains quarantined. Video stays at the
flashed audit image's 2048-byte/125-us endpoint configuration, and audio stays
48 kHz mono S16 with alsaloop's existing 50-ms target latency.

## Why the existing evidence is insufficient

The audit image has confirmed missed USB payloads and host JPEG failures that
concentrate during microphone capture. Its encoder reports no buffer failures.
The first stream also produces only about 25 source frames/s; transfer failures
alone do not establish the reason for that source-rate shortfall.

All periodic ALSA snapshots missed active audio. Continuous host timestamps
cannot establish physical microphone delay. The USB driver's 16547 empty drops
in one stream resemble its 16384-microframe modulus, but the existing aggregate
counter cannot distinguish a single recovery burst from independent misses.
The helper-level wrap probe does not establish a reachable target failure.

Additional source checks: UVC request allocation is capped at 64, so the raw
image-size field does not create an unbounded USB request backlog. Target logs
identify the alsaloop playback-pitch control; automatic software resampling is
not the chosen synchronization mechanism. JPEG failures occurred between the
periodic SD-log snapshots in the controlled microphone window, so those writes
do not explain that failure window. None of these exclusions prove a fix.

## New evidence collected

- Microphone supervisor snapshots at roughly 1 second after launch, then every
  5 seconds, plus a separately labeled pre-stop snapshot. Each includes PCM
  status/delay, hardware parameters, child CPU accounting, and CPU frequency.
  Reading procfs does not open another PCM or interrupt alsaloop with a signal.
  Collection stops after 512 snapshots per supervisor process to bound RAM use.
  Procfs delay excludes any samples in alsaloop's userspace buffers and host
  buffering: it is not an acoustic end-to-end latency measurement.
- The system logger copies new microphone log bytes without the old 80-line
  truncation, mounts debugfs, and saves DWC2 parameters plus recovery counters.
- DWC2 counters identify start-request, endpoint-disabled, OUT-token, and NAK
  recovery separately, with total/payload drops and maximum requests expired
  in one recovery pass. First, latest, and largest burst *start* samples retain
  monotonic time, session number, cached/live frame, target, overrun flag, and
  last endpoint IRQ flags. Counters survive endpoint reopens until reboot.
  Last IRQ flags can precede process-context queueing and are not asserted to
  be the causal interrupt. DDMA errors are not covered by these non-DDMA sites;
  the captured DMA parameters determine which path is relevant.
- There is no IRQ printk. Successful transfers add only last-IRQ bookkeeping;
  clock reads and one snapshot copy occur at a recovery pass's first drop,
  with at most one additional worst-sample copy per pass. Debugfs copies each
  endpoint's small snapshot under the controller lock and formats after unlock.
  Actual observer cost on the Pi remains unmeasured.

No endpoint scheduling, frame-wrap arithmetic, recovery decisions, microphone
format/latency, camera controls, or encoder algorithm are changed.

## Offline verification

`check-mic-supervisor.py` runs the actual C supervisor with fake ALSA controls
and real child processes, including initial active state, queued events, rapid
close/open, irrelevant controls, crash retry, and bounded child shutdown. It
also requires periodic and pre-stop snapshots with the fake active PCM data.

`check-dwc2-diagnostics.py SOURCE_ROOT` extracts and compiles the actual helper,
checks its four call sites, and tests per-path counts, first/last/worst context,
retention, and a 16384-request burst with only one frame-clock read. This tests
diagnostic accounting, not hardware timing or wrap-bug reachability.

`check-diagnostic-log.py SHELL [ARG ...]` verifies complete capture of more than
80 log lines, incremental reads without duplication, and file truncation.
Tested with macOS /bin/sh and the matching BusyBox hush.

Independent read-only review found no USB behavior mutation and requested the
per-pass worst-sample copy optimization and clearer sample labels. Both were
implemented. Kernel/microphone cross-build and artifact verification are
recorded separately when complete.

## Interpreting a future capture

`bash diagnostics/run-concurrent-capture.sh` automates fixed 720p video for
150 seconds, with 120 seconds of microphone capture in the middle, followed by
a 20-second native combined capture and a 70-second save window. It records
actual event times, raw microphone WAV, native frame/audio results, and macOS
USB logs. It does not access storage devices. The longer active window is
machine-controlled; it does not require repeated card swaps. This wrapper has
been syntax checked, not run against the currently disconnected Pi.

A large maximum recovery burst plus its live/cached/target states can support
or reject the wrap-recovery hypothesis. Scattered small bursts point elsewhere;
DMA mode and IRQ state narrow the next trace. Active capture and playback delay
show whether a backlog is already on the Pi. These measurements still need
physical sound-to-host timing to establish the user's perceived microphone lag.

## Verified artifact

`sdcard-transport-diagnostics.img`, 41394688 bytes. SHA256:
`de63a4179bced85db70328d57db6cdf5d51f0240e86c28fcf8012bb654a9efd2`.
Rootfs differs from the flashed audit image only at the supervisor and logger.
Kernel SHA256 `49d245b2c9148d0dad4c24f2383ee32841eae5f4196b3383722682cfa053009f`.
Cross-build exits0. Packaged FAT kernel and squashfs match exported build files,
and host exports match independent hashes computed inside the build volume.
No physical drive was written. No hardware performance/latency validation yet.
The previous endpoint-timing trial remains held; this image retains baseline
endpoint settings and changes diagnostics only.
