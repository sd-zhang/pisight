# UVC audio settings: hardware test — 2026-09-28

Simultaneous camera/microphone capture remains near 30 fps. New UVC audio Apply
and diagnostics enable/disable work on the physical Pi. Defaults were restored;
diagnostics is off in RAM and saved settings. No Save request was issued.

User reported flashing `sdcard-audio-settings.img`, SHA256
`244a83b7ad1cad01d9df80f99996fda27e62de0b45a22f3fb88e0a0393186c39`.
Actual card bytes were not independently hashed. New selectors 3/4, default
values and frame-aligned kernel policy were confirmed on the connected device.
No physical shutter state was requested or established.

## Concurrent capture

150-second 1280×720 video capture; mic open for the middle 120 seconds:

| Measurement | Previous camera-work image | Audio-settings image |
|---|---:|---:|
| Mic-on distinct video fps | 29.951 | 29.960 |
| Mic-on JPEG errors over about 117 seconds | 7 | 6 |
| Long-session microphone process CPU | 4.833% | 9.066% |
| First two sessions: video NAK payload misses | 18 | 11 |
| Video disabled payload misses | 0 | 0 |

Before/during/after microphone distinct fps: 29.890 / 29.960 / 30.044. Overall
4480 unique images from 4480 callbacks. Six mic-on decoder errors remain rare;
this run is not evidence that the residual USB error mechanism was eliminated.
The 20-second native combined capture had 598 unique images, 29.940 PTS fps,
961024 audio samples over 20.021333 s at 48 kHz and zero timestamp gaps >1 ms.

FFmpeg's 120-second run produced 107.019 seconds of WAV samples, similar to
prior host FFmpeg runs (106.048 seconds previously). The WAV alone does not
prove continuity. Independent native 20- and 90-second captures do, within
their measured intervals. Captured WAV peak 1319, RMS 32.029 PCM units; this
ambient recording is not a controlled speech or acoustic latency test.

## CPU / target state

Mic process CPU 9.066% over 116.148 seconds, versus 4.833% before the filter
plugin was added. The second short session measured 9.348%. This comparison
includes both the newly deployed filter and tuning/meter machinery, and does
not isolate individual costs. No hardware baseline exists for fixed-filter-only.

Aggregate CPU windows measured 70.516% (uptime124.76–188.09) and 71.550%
(188.09–252.67). Both include small mic-off portions; there is no fully active
aggregate snapshot pair this run. Previous fully active CPU was67.922%, so
report approximately71–72% for the mostly active interval, not an exact
like-for-like delta. Camera thread costs remain similar (18.31%,14.22%,6.58%).
The larger microphone cost leaves headroom and did not collapse video FPS.

ALSA combined queues:45.917–50.646ms, median48.990ms. These sequential queue
readings do not measure acoustic latency. Encoder final4496/603frames, all
failed/corrupt/invalid/timeouts/resets zero. Boot partition read-only in all
retrieved snapshots. No raw I2S boot probe ran with default diagnostics off.

First two sessions:140201 audio schedules,140200arms,1late (max115us),0early,
0resync; 11video NAK payload misses,0disabled video payload misses. Five total
incomplete interrupts across the sessions, not the old recurring IRQ storm.
Do not claim the rare late event or residual errors are fixed.

## Hardware UVC controls and diagnostics

GET_LEN/GET_INFO returned32bytes andGET/SET support for both new selectors.
Initial audio requested `[0,80,8000,0]`; diagnostics desired/saved0.
Temporarily enabled diagnostics without Save. During the later simultaneous
capture, these presets reached applied readback with recent-audio activity:

1. −6dB,120HzHP,12kHzLP,filter enabled.
2. 0dB,80HzHP,8kHzLP,bypass enabled.
3. Original0dB,80HzHP,8kHzLP,filter enabled.

Each applied acknowledgement arrived within the200ms polling interval. Meters
updated during capture, clipping counts zero in sampled readbacks. This proves
live processor handoff/readback; no calibrated acoustic gain/response measurement
was performed. Save/persistence on physical hardware was deliberately not tested;
it was verified offline in the prior turn. No SD settings changes were requested.

Diagnostics disabled during the90-second combined capture. Snapshot readback
at disable and84.242seconds later was exactly173542bytes with identicalSHA256
`49d1f00ae8244be018b6dcd1269a898de9544d39596f018663879f4c1e6675c5`.
This crosses the60-second collection interval and verifies collection stops.
Final flags show no unsaved audio/diagnostics changes. The4MiB rotation limit
was tested offline; this hardware log did not reach it.

## Bulk readback caveat and recovery

The90-second combined capture included a full173542-byte log download while
streaming. It ran approximately10.808–20.292seconds after the first video frame.
The10–20second window fell to23.907 distinct fps with14JPEGerrors, coinciding
with that transfer. Small audio setting requests were at4.15/6.37/8.59seconds;
the early decoder errors were at1–2seconds, before those changes.

Video recovered afterward:20–80second window29.964distinct fps,1JPEGerror.
Whole90-second session29.994PTSfps,2629unique images/2698callbacks (69repeats),
4320768audio samples at48kHz over90.016seconds,zero timestamp gaps >1ms.
Thus bulk log downloads can briefly interfere with video; no lasting collapse
was observed. Future app should avoid or throttle bulk downloads during calls.
Normal control read/write and a full log download have very different traffic.

Post-readback transport delta: one additional video/audio session,25video NAK
payload misses,0disabledvideo payload misses,0additional late/early audio enables,
1cancelled audio arm. Additional misses are not all assigned to a specific instant
by these aggregate counters; the host decoder timing above localizes the burst.

## Evidence and scope

Raw host/target logs, UVC transactions, WAV, summary.json, cpu-windows.json,
transport-summary.json, post-readback-windows.json and uvc-test-result.json are
in this directory. hardware-test.py is the one-off test harness, not a new product
CLI. No firmware edits, image rebuild, USB serial, drive writes, sound playback,
Save requests, commits or pushes were performed. Capture processes exited;
original audio defaults and diagnostics off were restored and read back.
