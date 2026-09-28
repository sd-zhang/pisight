# Building and validating PiSight

The repository contains `webcampi` as a submodule, with Buildroot nested inside
it. The current target is the original ARMv6 Pi Zero, not the Zero 2 W.

```sh
git clone --branch pizero-hw-mjpeg-encoder --recurse-submodules https://github.com/sd-zhang/pisight.git
cd pisight
./build.sh
```

Run the build on **x86-64 Linux** with Buildroot's host dependencies installed.
The pinned Bootlin toolchain is distributed for that host architecture. On an
ARM Mac, the verified setup uses Docker Desktop with a `linux/amd64` Linux
container and a Linux volume for the build tree. Native macOS is not a supported
Buildroot host; a native arm64 Linux attempt did not provide the selected
external toolchain. The project's scripts do not create or manage Docker for you.

The root wrapper delegates to `webcampi/build.sh`, which selects
`webcampi_raspberrypizero_defconfig` and builds the image. Output:
`webcampi/buildroot/output/images/sdcard.img`. No image is supplied by a clone.
Flashing is a separate user action; none of the build or offline test commands
writes a physical drive.

## Existing local build environment

The accepted image was built using `pisight-build-env:2026-09-26`, with the Linux
volume `pisight-build-work-amd64` mounted at `/work`. These are local resources,
not images published by this repository. `/work` contains the external tree and
`/work/buildroot` contains Buildroot. ARM emulation uses the local
`pisight-emulation:arm64` image with `qemu-arm-static -cpu arm1176`.

When copying sources, retain executable permissions and exclude macOS `._*`
metadata. Export results through a tar stream, then compare SHA-256 hashes on
both sides. Direct copies from this volume into a Mac bind mount previously
produced zeroed image data despite reporting success.

After changing local packages, use the corresponding Buildroot rebuild target.
When changing a patch, re-extract/repatch that package or explicitly apply the
new patch to the existing build source; a rebuild alone does not reapply patches.
Never silently claim an old compiled source represents a newly edited patch.

## Checks

The [diagnostics index](../diagnostics/README.md) describes offline regression
checks, target-source fixtures and the hardware measurement procedure. Most
checks use a system C/C++ compiler and Python 3. Buildroot integration checks
also need patched source trees, BusyBox hush, jq, and the ARM toolchain.

A hardware test must capture **camera and microphone together**. Separate camera
and microphone success is insufficient. Count distinct video images and decode
errors, and inspect audio timestamps. Queue depth is not acoustic latency.
Keep scene/exposure differences and snapshot boundaries in CPU comparisons.

Diagnostics is off by default. Enabling it through UVC is a RAM change unless
explicitly saved. Restore it afterward, and download bulk logs after measuring
steady streaming. A full log download can temporarily reduce video delivery.

## Commits and publishing

Commit firmware changes in `webcampi` on a named branch, then update its pointer
in this repository. Buildroot is pinned and needs no new commit for external
board/package patches. If publishing, push the nested `webcampi` commit before
pushing the parent pointer so another clone can resolve it. The cleanup commits
are local until explicitly pushed; they are not a release.

The working baseline, its image hash and current limits are in
[DEBUGGING_NOTES.md](../DEBUGGING_NOTES.md). Older design notes and reports are
historical evidence. Generated images, captures, raw logs and compiler output
are kept locally and ignored; source tests and written reports are committed.
