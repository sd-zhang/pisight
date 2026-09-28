# Coalesced USB fix: hardware capture — 2026-09-27

User reported flashing the candidate and reconnecting. Named iSight enumerated
at480Mb/s. Ran the same150s720p video capture with120s microphone in the middle,
then20s native simultaneous capture. Host results show no meaningful recovery.
This confirms the narrow ownership fix did not solve the simultaneous A/V
failure. The exact target kernel and post-fix recovery state require card log
readback; USB identity alone does not verify the flashed image.

| Stable window | Prior fps | New fps | Prior JPEG errors | New JPEG errors |
| --- | ---: | ---: | ---: | ---: |
| Mic closed before |26.181|26.409|0|0|
| Mic open |19.422|19.487|462|457|
| Mic closed after |26.293|26.464|1|1|

New stable mic-on window116.554s. Maximum changed-image gap461.7ms.
Full toggle decoder3128completed/467dropped (previous3072/484). Scene and
exposure are uncontrolled across boots; small numerical differences cannot be
attributed to the patch. The within-run mic-on slowdown remains reproducible.

Native combined reopen:350distinct images,245consecutive repeats,17.601unique
fps (previous359distinct,238repeats,18.059fps). Decoder366completed/70dropped.
Audio960512samples at48kHz over20.0107s, zeroPTS gaps>1ms. Continuous timestamps
do not establish acoustic latency or absence of corruption before host capture.
FFmpeg microphone recording has5156864samples (107.435sample-seconds), RMS438.54,
8999distinct sample values; its known AVFoundation pending-buffer overwrite
possibility prevents attributing the120s timestamp/sample-count shortfall to Pi.

No target settings changed, new image built, or physical drive written during
this test. Do not claim smooth simultaneous A/V or propose a further speculative
flash. Saved events, host USB logs, raw microphone and capture JSON are here.
The70s target logger save window completed and the capture script exited0. Next target evidence is PISIGHT.TXT from this boot to compare
recovery counters and determine whether premature retirement disappeared while
other disabled transfers persisted. No live file-access path exists on the
currently configured UVC/UAC2-only device.
