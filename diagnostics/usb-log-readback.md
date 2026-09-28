# PiSight diagnostic readback over the existing webcam USB connection

Purpose: stop requiring SD-card extraction just to retrieve logs. This is a
diagnostic-access addition, not a video/audio performance fix. The current
flashed coalesced-fix image lacks this addition. Hardware readback remains
untested until firmware containing patch0016 is installed by the user.

`webcampi/package/uvc-gadget/0016-uvc-diagnostic-readback.patch` adds selector2
to the existing `PiSightSettings1` extension unit. Explicit bNumControls2 and
bitmap0x03 retain selector1 settings and add diagnostic paging. No new USB
interface, endpoint, network, serial function or kernel patch. Video endpoint
2048bytes/125us, audio buffering and HW encoder settings remain unchanged.

Supported fixed read-only sources:

- source0: `/tmp/PISIGHT.TXT`, the existing periodically appended diagnostic log.
- source1: `/sys/kernel/debug/usb/20980000.usb/isoc_stats`, live USB counters.

No arbitrary path, command execution, or target-file write is accepted. A
host-triggered snapshot allocates at most4MiB, reads one source, and serves an
immutable copy. The source log can end during a concurrently appended section;
the copied bytes are immutable during retrieval. A new snapshot/release/device
close/disconnect frees the old snapshot. No snapshot allocation at boot.
Retrieve after A/V measurement: allocation, file I/O and repeated EP0 traffic
are additional work while requested and must not contaminate a timing test.

Usage after the updated firmware is running:

```
python3 diagnostics/read-usb-diagnostics.py --source log --output diagnostics/target-next.log
python3 diagnostics/read-usb-diagnostics.py --source usb --output diagnostics/counters-next.log
```

Reader uses the already-installed Homebrew libusb and discovers the XU's unit
and interface in actual descriptors. It rejects settings-only firmware, short
transfers, wrong version/generation/offset/total/length/EOF/padding and target
errors. It prints a SHA256 and writes output only after protocol validation.
Existing output files are not overwritten. Commands only select/read/release a
snapshot in RAM. No physical drive is opened by the reader.

## Protocol v1

The control is60bytes, matching the actual Linux `uvc_request_data.data[60]`
limit. GET_LEN returns60 and GET_INFO returns GET/SET support. GET_CUR is
idempotent, so repeating a read cannot skip data. SET_CUR data stages must have
exactly60bytes. Invalid channel, interface or direction is rejected at setup.
Diagnostic setup/data events skip verbose per-control logging to avoid log
amplification. Other controls retain their existing routing/logging.

Command bytes: version1, operation, source, reserved0; little-endian generation
at4 and offset at8; bytes12–59 must be zero. Operation1 snapshots source0/1
with generation/offset0; operation2 selects an absolute offset in the current
generation with source0; operation3 releases with remaining fields zero.
Response bytes: version1, status, payload length0–44, EOF0/1; generation at4,
total size at8, offset at12; payload at16, remaining bytes zero. Status0 success,
1 no snapshot,2 file error,3 offset error,4 invalid/stale request,5 oversized,
6 allocation failure. A snapshot generation changes on each successful capture.
The host uses both generation and total length to reject interleaved snapshots.

## Verification

Tests live in `diagnostics/usb-log-regression/`. Baseline actual UVC control
handler fails new selector GET_LEN; patched handler and setup-routing tests pass.
Tests use the real bundled UVC request-data layout, rather than assuming the
full64byte USB EP0 packet fits the60byte userspace event payload.

Native C protocol tests compiled with warnings as errors and UBSan cover binary
pages, retry stability, source append isolation, EOF, wrong offset/generation,
malformed commands, missing/empty/oversized sources and release. Host test feeds
actual C responses through the Python reader and compares255251 binary bytes
exactly, then injects truncated/corrupted responses and confirms rejection.
Descriptor test executes the actual setup fragment against a default zero
control count. The kernel does not infer bNumControls from bmControls; the
explicit count correction is required and tested.

Independent review found and resolved malformed-selector fallback, missing
disconnect subscription, and descriptor-count concerns. All final native tests
pass. Build/image verification and hashes are recorded below when complete.
No claim of hardware readback or A/V recovery follows from these offline checks.


## Built candidate

`diagnostics/sdcard-usb-log-readback.img`,41,398,784bytes, SHA256
`63995b85fcd6601b0673935f08ed88c076133dac651d0d3f62dd155309ec8b09`.
Final ARM build exited0. Tar-stream export hashes match Linux build artifacts.
Image partitions verified; every boot file including kernel is unchanged from
the flashed coalesced-fix image. Rootfs inventory changes only
`usr/lib/libuvcgadget.so.0.4.0` and `usr/local/bin/uvc-gadget.sh`. Script bytes
match the tested source. Exact verifier: `verify-usb-log-image.py`; results
`usb-log-image-verification.txt`. Final build emits the pre-existing unused
`pu_control_name` warning and four nonfatal Buildroot inventory `comm` notices;
no new compile error. No card writes, commits or pushes.

`run-concurrent-capture.sh` now attempts target log and live-counter retrieval
after capture and the existing70s save window. On unsupported firmware it records
the readback error without discarding successful host measurements. Shell syntax
checked; automatic hardware readback has not yet been run. The standalone
reader also remains available. After this candidate is installed and readback
verified, routine log extraction should no longer require SD removal.

Build source staging `/private/tmp/pisight-usb-log/{base,new}`. Docker build
volume/output now includes patch0016, with timing-trial0015 still held.
