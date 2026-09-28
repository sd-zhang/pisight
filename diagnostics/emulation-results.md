# Packaged ARM userspace smoke check (2026-09-27)

Runtime: `pisight-emulation:arm64`, built from `diagnostics/Dockerfile.emulation`.
Includes QEMU 8.2.2 system ARM and static ARM user emulator, native jq 1.7.1,
Python 3 and squashfs-tools. No host packages or privileged container required.

Tested the existing held `/work/buildroot/output/images/sdcard.img` from Docker
volume `pisight-build-work-amd64`, mounted read-only. This was the existing
mic-gating image, before the ongoing encoder/audio/settings fixes were built.
Read the second MBR partition into a temporary file, extracted it using
`unsquashfs`, and copied the host-native static ARM emulator into that disposable
root. Production image, source volume, repository scripts and physical devices
were unchanged.

Actual commands within that disposable root:

```
chroot ROOT /usr/bin/qemu-arm-static /bin/busybox sh -c 'echo SHELL_OK; /usr/bin/jq --version'
# exit 0: SHELL_OK; jq-1.8.0
chroot ROOT /usr/bin/qemu-arm-static /usr/bin/jq --version
# exit 0: jq-1.8.0
chroot ROOT /usr/bin/qemu-arm-static /bin/busybox sh -c 'set -eu'
# exit 1: sh: set: -eu: invalid option
```

This verifies execution of the packaged ARM BusyBox and jq, and reproduces the
unsupported hush flag with the actual packaged executable. It does not test
settings persistence, init environment inheritance, supervisor behavior, kernel
boot, camera, MMAL encoder, audio timing, USB gadget transfers, or final rebuilt
image contents. Full system boot was not attempted. Work stopped when the task
was narrowed to avoiding unnecessary emulation setup.

Reuse the runtime without installation:

```
docker run --rm --platform linux/arm64 pisight-emulation:arm64 jq --version
```

Use `--mount type=volume,src=pisight-build-work-amd64,dst=/work,readonly` for
read-only access to existing build artifacts. Extract image partitions only to
disposable container storage before running a chroot.

## Final candidate launch/linkage check

The final sdcard-audit-fixes image (SHA256
0a69a8605ed87fcf707f01f42318def9d1cd8231b9982f407b0c1a0df19b4327) was
extracted from its actual second partition into a disposable container root.
The packaged ARM BusyBox parsed S60 (exit0), jq --version ran (exit0),
uvc-gadget -h ran (exit0), settings-store rejected missing arguments (exit2),
and pisight-mic loaded and rejected the absent ALSA hardware (expected exit1).
No shared-library loader errors. These are launch checks, not boot or media
tests; full system emulation was not pursued.
