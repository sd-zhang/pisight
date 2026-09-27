# PiSight development handoff

This repository has nested submodules: `pisight` -> `webcampi` -> `buildroot`.
Work on branch `pizero-hw-mjpeg-encoder`. On a fresh computer:

```sh
git clone --branch pizero-hw-mjpeg-encoder --recurse-submodules https://github.com/sd-zhang/pisight.git
cd pisight
git submodule update --init --recursive
```

The top-level branch pins the `webcampi` commit. A detached `HEAD` inside a
checked-out submodule is normal; create a branch there before making new
`webcampi` commits, and push that branch before pushing the updated top-level
submodule pointer. Do not accidentally commit generated Buildroot output or
personal `.idea` files.

Read `DEBUGGING_NOTES.md` before changing USB/audio/video behavior. The current
source includes the hardware MJPEG encoder, UVC settings, I2S ICS43434 overlay,
and UAC2 microphone. The user's latest observed result was a silent microphone
and video that eventually started with very poor frame rate. A mock-ALSA test
reproduced high-priority `alsaloop` CPU use when the host does not record audio;
this is a plausible contributor, **not** a confirmed explanation of the Pi's
full failure. Do not claim either issue fixed without target measurements.

The user wants to avoid repeated image flashes. Earlier USB serial/network
composite-gadget attempts degraded UVC; keep diagnostics on the existing
UVC/UAC2 gadget when possible. The current image has no SSH or USB serial
console. If the existing diagnostic card has `/boot/PISIGHT.TXT`, analyze it,
but its logger only writes after UVC `STREAMON`, daemon death, or a long timeout;
absence of the file proves little. The one-off diagnostic image and its build
script are local, untracked artifacts documented in `DEBUGGING_NOTES.md`.

For a fresh build, use a Linux environment (a Linux VM is needed on macOS):

```sh
cd webcampi
./build.sh
# Result: buildroot/output/images/sdcard.img
```

The top-level `build.sh` still runs an obsolete `device-info.patch` step; use
`webcampi/build.sh` directly until that wrapper is cleaned up. Generated SD
images live under ignored `webcampi/buildroot/output/` and are **not** supplied
by `git clone` or `git pull`. The last normal image on the prior Linux build
host was SHA-256 `e9d89da16f7150d1bb7da683c9048210263992544cab0065718be14a7a431fbf`.

The next useful no-flash test is fixed-mode 1280x720 MJPEG frame timing plus
raw 48 kHz mono USB-mic capture on the same host, with microphone capture
closed, open, then closed while video remains open. Inspect raw samples and
the bridge log before changing the audio path. Discord's processing alone
cannot tell whether the USB PCM samples are silent.
