# Audit corrections — 2026-09-27

User requires acting on audit results before another flash. Continue in the existing audited branch/checkouts, preserving uncommitted prior work and .idea. No commits, pushes, or physical drive writes. Docker Desktop build volume permitted; no OrbStack. Existing candidate remains HOLD.

## Plan
1. Settings: explicit supported exports in both S60 sources; regression executes real init/config path with matching hush and tests child environment; settings save happy path/error cleanup as feasible.
2. USB/audio: restore active-state notification on resume without restarting already-enabled endpoints; regression active/inactive suspend/resume; ensure coalesced host sessions reset bridge safely. Keep evidence-based audio/USB tuning separate from unproven guesses.
3. Encoder: safe drop/recycle on zero/error/truncated output; reset partial queue errors; nonblocking bounded/cancellable codec waits; synchronized queue/abort state. Add real-code error-injection tests and timing/error counters.
4. Integrate/review: inspect every change and test; apply patches to pristine pinned sources; cross-build kernel/userspace; export image through tar; verify checksums and exact rootfs contents. Update audit disposition with tests and remaining hardware limits.

Interfaces: 1 changes S60 only, 2 owns new kernel UAC2 patch and pisight-mic supervisor/tests, 3 owns new userspace patch and encoder tests. Root owns build volume mutations and final integration. Agents may read build volume; avoid simultaneous build mutation. Diagnostic counters may require separate kernel UVC patch owned by root.

Ruling: no speculative change to USB packet bandwidth or ALSA period sizes absent proven cause. Correct defects and expose stage/error timing so next run distinguishes remaining hardware causes.

## Progress
- Plan and ownership established; implementation underway.

- Settings: real init/config shell test failed before fix (all six child variables missing), passes after explicit exports. Real jq persistence/update cleanup also pass. Test fixture output made atomic to avoid observing an empty background env file.
- Audio: resume patch and relevant-rate refresh implemented; production-function kernel harness and five supervisor scenarios pass.
- Encoder: safe recycle, error validation/reset, nonblocking cancellation, synchronized mainloop dispatch and teardown implemented. Actual codec 16-case injection test and source ownership test pass; baseline reproduces failures.
- Independent integrated review found no blocking issue; explicitly retained limits around kernel STREAMOFF/close and hardware DMA/concurrency.
- Patches staged/applied to existing build volume after dry-runs. Cross-build running; applied hashes in /work/diagnostics/applied-audit-patches.sha256.
- User asked whether VM testing necessary then asked for judgment: dropped optional full-system VM work. Existing ARM userspace emulator was prepared and ran baseline BusyBox/jq; no full boot attempted. Keep final checks targeted.

- Kernel and initial integrated image build exited 0. Final camera compile additionally addressed notification EINTR/read handling, with source regression coverage and scoped review approval. Final uvc rebuild/repack underway; all 14 final patches reproduce compiled sources from the pristine pinned archive.
- Emulation boundary: a full VM was not required or attempted. Actual baseline ARM BusyBox/jq ran in a disposable extracted root; no production image or drive changes. No further VM setup planned.

## Completion
All planned code corrections, scoped regression tests, clean camera patch-series check, independent review, kernel/userspace builds, and image export/content verification complete. Candidate sdcard-audit-fixes.img SHA256 0a69a8605ed87fcf707f01f42318def9d1cd8231b9982f407b0c1a0df19b4327. Actual packaged ARM binary smoke checks pass. Hardware performance remains unmeasured; no physical drives written. See DEBUGGING_NOTES.md for full verification and exact remaining limits.
