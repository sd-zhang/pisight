# Baseline commit verification — 2026-09-28

The user accepted the hardware results, then requested cleanup, documentation
and local commits. Runtime firmware was not changed during cleanup. The nested
firmware commit is `9dd445f` on `pizero-hw-mjpeg-encoder`; Buildroot is unchanged.

Fresh checks before committing:

- Six microphone supervisor lifecycle scenarios, including diagnostics off.
- Native UBSan DSP and control tests: gain/cutoffs/bypass, crossfade, saturation,
  quiet tails, async Save/error handling, atomic IPC and diagnostic settings.
- Diagnostic snapshot gating, rotation and cancellation; incremental log reads.
- Real settings scripts under BusyBox hush with jq: exported boot settings,
  Save/reload, field preservation, invalid input, error cleanup and writer lock.
- Actual UVC selector routing and descriptor setup.
- Actual DWC2 SOF audio arming, incomplete-event guards, 101 completion/recovery
  cases and 11 diagnostic sampling cases; UAC2 resume callbacks.
- Actual LED and shutter stream lifecycle checks.
- Packaged ARM1176-emulated DSP, live settings, bypass edge cases and actual ALSA
  plugin/route: split reads, prepare/restart and incompatible-format rejection.
- Image/source-hash and filesystem comparison: accepted image remains
  `244a83b7ad1cad01d9df80f99996fda27e62de0b45a22f3fb88e0a0393186c39`.
- Root build wrapper shell syntax and delegation from an unrelated directory
  containing spaces, including propagation of the child exit status.
- Staged-file inspection: text/source only, no images, recordings or binaries.
  Unified-diff context whitespace is preserved through patch-specific attributes.

All listed checks passed. Detailed output remains local in
`/private/tmp/pisight-cleanup-{supervisor,integration,arm}.txt`; prior source and
hardware reports remain in this directory. Documentation review found two issues
that were corrected: missing Dockerfile allowlisting and an overly narrow
attribution of the audio CPU increase. No new flash or hardware capture was
required for this documentation/build-wrapper cleanup.

The top-level build wrapper now delegates directly to the firmware tree. The
obsolete product-identity patch step was removed; identity already lives in the
firmware patch stack. Historical notes are archived, the current handoff is
concise, and generated evidence remains local and ignored. Commits are local;
no remote push or release is implied.
