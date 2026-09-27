# PiSight USB video and microphone handoff (2026-09-26)

## Current result on the Pi Zero Rev 1.3

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
