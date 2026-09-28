# Camera work reduction — implementation and verification

User approved trying the two camera-side redundancies identified in
remaining-cpu-audit-20260928.md. The candidate is ready, not hardware-tested.

## Changes

`webcampi/package/uvc-gadget/0021-submit-camera-controls-on-change.patch` tracks
pending crop/EV settings. Setters ignore unchanged values. The main event loop
submits the latest settings once; libcamera retains absent controls. Every stream
start forces an update, including new crop bounds following reconfiguration.

Review caught asynchronous request cancellation: queueRequest returns success
before queueRequestDevice necessarily succeeds. Pending state is now atomic and
consumed BEFORE queue submission; an active cancellation callback marks it dirty
again, and synchronous rejection restores it. Callbacks never read crop/EV values.
This prevents a cancellation notification being erased by a successful return.
Existing cancelled-request pool shrink is not changed; surviving requests retry.

`webcampi/board/raspberrypizero/patches/libcamera/0002-cache-vc4-lens-shading-geometry.patch`
caches only sampling indices and phases in the IPA instance, keyed by both grid
dimensions (maximum64x49). Original floating-point accumulation, interpolation,
rounding and saturation are retained; input gains are read and recomputed every
frame. Cache survives modes safely because geometry depends only on dimensions.
No lower algorithm cadence, frozen settings, raw frame copy, or USB change.

## Tests and build

- Test-first baseline fails for100 unchanged control transmissions; lens baseline
  fails for repeated coordinate calculations while numerical output is correct.
- Initial candidate cancellation test fails for a lost accepted update; corrected
  atomic exchange-before-submission and dirty callback pass.
- Native and ARM1176 emulation execute actual extracted production methods.
 7,634,088 old/new lens output values match, with additional independently expected
  unity gain1024 and saturation16383. Varying values, width/height transitions and
  rounding boundaries covered. Reference fixture is retained with its BSD license.
- Actual setters, request queue, completion callback, stream_on/stream_off methods
  exercised against a fake hardware boundary. Covers mixed updates, repeated
  values, invalid inputs, unsupported controls, stopped-state updates, restart,
  simulated crop reconfiguration, synchronous/asynchronous failures and a
  cancellation callback during queueRequest. Full allocator/hardware is not mocked
  as a faithful target simulation; integration is separately ARM compiled.
- Existing actual-source shutter and LED tests pass. No central project test
  command exists for these downstream patches. Unchanged USB timing code was
  verified by packaged kernel identity instead of repeating every kernel replay.
- Full libcamera and uvc-gadget ARM builds and Buildroot image build exit0. Existing
  Buildroot `comm` missing .files-list.before inventory warnings remain nonfatal.
- Independent review initially identified cancellation handling and lifecycle test
  gaps; both addressed; final reviewer found no remaining blocker.

## Focused performance evidence

Native Mac interpolation benchmark:1.18443us ->1.03723us per42x25table (~12.4%).
Final ARM1176-emulated benchmark after build completed:74.8061us ->71.439us (~4.5%).
Earlier emulator measurements varied, particularly while the image build ran.
Coordinate caching saves limited work; most interpolation arithmetic remains.
These results are not Pi cycle timings or whole-camera CPU savings. The avoided
per-frame crop/EV path was verified by submitted requests, not assigned a measured
CPU percentage. Actual CPU/FPS and hardware setting behavior remain unverified.

## Exact artifact verification

Image: `sdcard-camera-work.img`,41423360bytes.
SHA256: `95ecfd3891d2462178578b7b4f1b33cbe9a2c4c2806867ecf481cb14bdbec267`.

`verify-camera-work-image.py` checks compiled source hashes and exported file
hashes, embedded rootfs, every boot file, and signed IPA against the public key
embedded in unchanged libcamera. The rebuilt FAT contents match the working image;
its entire tested FAT partition is preserved, including metadata. Kernel unchanged.
Root filesystem inventory differs in exactly libuvcgadget, IPA module and signature.
Everything else, including mic bridge, shutter, diagnostics and boot config, matches.

Sources and exports: /private/tmp/pisight-camera-work/{base,new,export,root}.
Docker build volume contains both new patches and compiled source. Image creation
uses only regular files; no physical drives, serial, live captures, commits or
pushes. Original working image preserved. Microphone quality is a separate unresolved
issue. User alone flashes. Next hardware measurement can use the same concurrent
capture script and compare against capture-audio-sof-shutter-20260928/results.md.

Evidence files: camera-work-tests.txt, camera-work-arm-results.txt,
camera-work-arm-benchmark-idle.txt, camera-work-image-verification.txt,
camera-work-shutter-tests.txt, camera-work-led-tests.txt, build-camera-work.log.
