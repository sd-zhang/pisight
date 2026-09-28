# Three-minute simultaneous A/V follow-up

Same flashed audio-SOF image; no firmware changes, no reflash, shutter monitoring
still disabled. Capture started2026-09-28T05:45:48Z, ran180seconds, selected
named iSight camera and iSight Microphone.

- 5385 distinct images from5399 video callbacks:29.943 distinct fps;14repeats.
  Camera PTS cadence29.998fps; max arrival gap125.869ms. Six host JPEG decoder
  errors. UVC reports7payload misses and41empty misses in this stream, all NAK
  for payloads. Decoder-error and payload counts need not match one-to-one.
- 8641536 audio samples at48kHz over180.032seconds; zero audio PTS gaps>1ms.
  Target late audio enable count stayed1 across the entire longer run:
  no additional late event. One prepared request cancelled, consistent with
  shutdown; this is not evidence of a lost captured audio packet.
- The two new audio NAK payload events end at uptime720.186227; raw I2S PCM
  capture started720.261025 and gadget playback720.261195. Thus both occurred
  before ALSA microphone capture. One new audio disabled payload event is at
  stream closure. Do not equate these counters with audible steady-state loss.
- Two fully active target windows751.85→816.12 and816.12→880.45 had zero
  incompleteIRQ and zero audio NAK events; CPU67.25%/66.45%. No disabled video
  payloads anywhere in this run. The earlier recurring recovery failure stays
  absent while occasional video NAK misses remain.

## Logging hypothesis checked

Four errors from the earlier run overlapped a periodic snapshot near uptime197s.
In this follow-up, none of six decoder errors overlapped inferred snapshot work
windows751.85–756.12,816.12–820.45,880.45–884.83. The overlap did not repeat, so
there is no basis here to remove diagnostics or blame them for the remaining
misses. This rejects a simple direct-overlap explanation, not every possible
indirect effect of diagnostic work. Host/Pi clocks are approximately aligned by
stream teardown; logger end times are inferred from the next start minus the
script's60second sleep. See residual-error-timing.json for exact inputs.

The remaining path is DWC2 NAK recovery after an unserved host polling slot.
The saved first/last/worst samples and maximum handler duration cannot identify
which interrupt/critical section delayed each packet, nor establish whether
hardware DMA/FIFO scheduling also contributed. No justified additional driver
patch follows from this evidence alone. Preserve the functioning image.

Actual acoustic latency and subjective audio quality are still unmeasured.
The question about audibility of this Mac's speakers remains unanswered; no
sound was played. Continuous host timestamps do not rule out concealment by
host drivers. No USB serial, physical-drive writes, or card extraction.
Capture completed; target readback occurred afterwards.

Evidence: combined.json/log, host-usb.log, target.log, target-usb-counters.log,
irq-windows.json, counter-delta.json, residual-error-timing.json. Aggregate
counter comparison excludes first/last/worst timestamp records; replay with
`diagnostics/compare-usb-endpoint-counters.py BEFORE AFTER`.
