# Encoder audit corrections — 2026-09-27

Implemented in `webcampi/package/uvc-gadget/0014-encoder-safe-recovery.patch`,
sequentially after 0013. No old patches changed, commits made, build-volume
mutations performed, or physical drives touched by this task.

- Failed encodes retain the contiguous output sequence, then return their paired
  camera/destination slot on the main event loop without invoking the UVC sink.
- Reject V4L2 ERROR on either codec queue, zero/invalid/oversize payloads,
  invalid offsets/index/plane counts and JPEGs missing SOI/EOI. Never truncate
  an oversized JPEG into a seemingly successful frame.
- Every codec QBUF/DQBUF failure STREAMOFFs/closes the old codec fd before
  releasing its mappings or allowing source reuse. The next frame reopens,
  restores quality, configures and allocates fresh queues. Partial STREAMON
  and allocation failure also unwind.
- Both codec queues are O_NONBLOCK. DQBUF retries use a shared one-second frame
  deadline and 2 ms cancellation checks. Destructor cancellation precedes joins;
  abort flags are atomic. This bounds userspace waiting on stalled dequeues.
- Camera/encoder completions share a mutex and event-pipe handoff. Camera
  controls, request reuse and UVC submission now happen on the event loop.
  Stream-off stops new callbacks, joins workers before destroying requests,
  clears both completion queues and drains stale notifications.
- Destination capacity comes from imported UVC allocation, rather than the raw
  camera frame span. Stream summaries and first-error/every-300-frame codec
  summaries expose drop/corruption/invalid/reset/timeout counts and encode,
  OUTPUT-wait and CAPTURE-wait durations without per-frame failure logging.

## Executed regressions

Actual full built post-0013 source was exported read-only to
`/private/tmp/pisight-encoder-fix/base`; patched staging is its sibling `new`.
The tests compile actual `hw_mjpeg_encoder.cpp`, replacing Linux syscalls with
fault injection at link time. The source regression extracts the actual
completion/event dispatch/stream-off functions and supplies minimal camera
stubs; it does not pretend to emulate a whole libcamera pipeline.

Reproduce in the existing Docker build image (read-only mounts):

```sh
docker run --rm --platform linux/amd64 -w /tmp \
  --mount type=bind,src=/private/tmp/pisight-encoder-fix,dst=/fixture,readonly \
  --mount type=bind,src=/Users/steven/Documents/Git/pisight/diagnostics/encoder-regression,dst=/test,readonly \
  pisight-build-env:2026-09-26 /test/run.sh /fixture/new

docker run --rm --platform linux/amd64 -w /tmp \
  --mount type=bind,src=/private/tmp/pisight-encoder-fix,dst=/fixture,readonly \
  --mount type=bind,src=/Users/steven/Documents/Git/pisight/diagnostics/encoder-regression,dst=/test,readonly \
  pisight-build-env:2026-09-26 python3 /test/source.py /fixture/new
```

Final codec matrix: **16/16 PASS**, including successful fresh Configure/Encode
following partial CAPTURE QBUF failure. Final run timeout:1009 ms;
concurrent cancellation:31 ms. See `encoder-regression/patched-results.txt`.
Before fixes, the first 15-case matrix passed only normal encode and zero-return
at codec level; 13 failed. Before fixes, the source ownership regression aborts
on its explicit `bytesused != 0` sink assertion. After fixes, source zero drop,
subsequent success, stream-off notification draining and late callback
suppression all PASS. Baseline codec command adds `-e BASELINE=1` and uses
`/fixture/base`; baseline source command substitutes `/fixture/base`.

## Limits

Full production cross-build/patch-series checks are owned by integration.
Tests cover syscall outcomes, ownership dispatch and user-space deadlines, not
hardware DMA timing, kernel-driver deadlock, actual libcamera teardown, or
ThreadSanitizer race detection. STREAMOFF/close themselves depend on the kernel
completing; userspace cannot guarantee a deadline if a driver hangs inside
those calls. JPEG SOI/EOI validation catches truncation but is not a full JPEG
decoder. Wait-stage means are accumulated successful waits divided by all
attempts; total encode latency includes failed waits. Hardware video frame
rate, JPEG transfer integrity and microphone-open interference remain unproven.
The existing image stays HOLD pending integration and target measurements.

## Notification follow-up after cross-build review

The integration cross-build succeeded but reported three ignored pipe syscall
results. The final 0014 now retries interrupted completion writes, event reads
and stop-time draining; only a successfully consumed notification dispatches a
completion. Full-pipe EAGAIN is treated as already readable (the request pool
bounds outstanding completions below pipe capacity). Other errors produce one
diagnostic per stream, guarded atomically across callback threads.

Expanded actual-function regression PASS: interrupted output notification,
interrupted camera notification, interrupted event read, empty event read
preserving its queued completion, interrupted shutdown draining, and original
zero-drop/success/late-callback tests. Incremental patch for integration's
already-patched source: `/private/tmp/pisight-encoder-fix/encoder-pipe-incremental.patch`.
