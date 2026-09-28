# PiSight development handoff

## Current baseline

Work on `pizero-hw-mjpeg-encoder`. The user accepted the hardware-tested audio
settings image on 2026-09-28. Read [DEBUGGING_NOTES.md](DEBUGGING_NOTES.md) for
results, remaining limits and the next useful work. Do not treat old candidate
images or historical hypotheses as current instructions.

The enclosure is now sealed. The last confirmed installed image is the accepted
audio-settings baseline. The newer video-modes/software-reboot candidate passed
offline checks but has not been hardware-tested or confirmed installed. Keep
that distinction in future app work; do not assume selector 5 is on this unit.
Hardware verification is deferred until the user chooses to update the device.

The repository contains nested submodules: `pisight` → `webcampi` → `buildroot`.
Commit firmware in `webcampi` first, then commit its pointer in the parent.
Create a named branch before committing from a detached submodule checkout.
If publishing later, push the nested commit before the parent pointer. Commit
requests do not authorize pushes, merges, or releases.

## Hardware and operating constraints

- Target: original Pi Zero / ARM1176, Camera Module 3, hardware MJPEG, ICS43434
  I2S microphone, simultaneous UVC video and UAC2 audio.
- Never flash or write host physical drives. The user handles flashing.
- Docker Desktop is authorized for Linux builds; do not use OrbStack.
- Do not enable USB serial or networking. Earlier serial use caused persistent
  video degradation. Settings and diagnostic readback use the existing UVC XU.
- No host app, new product CLI, or web app is requested yet. Audio tuning and
  diagnostics capabilities are implemented for a future UVC app.
- Do not play calibration sounds or claim measured acoustic latency from PCM
  queue depth or continuous timestamps.
- Keep the accepted image and recordings locally. Generated images, recordings,
  build output and IDE files are excluded from Git; don't delete them casually.

## Development and verification

Use `./build.sh` on Linux; see [docs/development.md](docs/development.md).
The selected external toolchain requires x86-64 Linux. On this ARM Mac the
working setup is Docker Desktop with a Linux amd64 build container and a Linux
volume. Export images through a tar stream: direct copies to a Mac bind mount
previously produced corrupted files. Check image hashes on both sides.

Tests and evidence are indexed in [diagnostics/README.md](diagnostics/README.md).
ARM emulation verifies code and ALSA plumbing, not USB/DMA timing, CPU headroom
or acoustics. Preserve the tested USB scheduling while changing other features.
There is no single test that proves the entire firmware works on hardware.

Diagnostics default off. Enable temporarily through UVC before a capture when
snapshots are needed, then restore off without Save unless persistence is
requested. Bulk log downloads can briefly reduce FPS; transfer them after the
measurement. The existing capture shell script does not enable diagnostics.
Do not request SD extraction when UVC readback can provide the evidence.

The shutter sensor on this unit appears broken or miswired and did not follow
physical shutter movement. Its GPIO edge implementation remains, but physical
shutter operation is unverified and the user accepts a purely physical shutter.
