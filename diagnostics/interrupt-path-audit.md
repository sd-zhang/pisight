# Interrupt path audit, 2026-09-27

Status: no demonstrated A/V performance fix. The USB log-readback image is
held; the user was explicitly told not to flash it yet. This audit made no
firmware, image, or SD-card changes.

## Findings from the actual built kernel

Read `drivers/usb/dwc2/core_intr.c`, `sound/core/pcm_lib.c`, and `.config`
from `/work/buildroot/output/build/linux-custom` in the existing Docker build
volume, mounted read-only. Local combined extraction:
`/private/tmp/pisight-irq-source.txt`. DWC2 source with patch0006:
`/private/tmp/pisight-coalesced-fix/new/drivers/usb/dwc2/gadget.c`.
UVC/UAC source: `/private/tmp/pisight-stream-source/linux-custom/drivers/usb/gadget/function/`.

1. `dwc2_handle_common_intr()` reads DSTS into the cached frame number.
   `dwc2_hsotg_irq()` then dispatches endpoint events, with video ep1 before
   audio ep3, and handles the global incomplete-IN condition afterward.
   This is not an audio-first endpoint priority bug. The gadget interrupt
   initialization does not enable SOF interrupts; interpreting the idle
   roughly 1,000 USB IRQ/s as a measured SOF rate is unsupported.

2. `dwc2_hsotg_complete_request()` drops the controller spinlock around the
   gadget completion callback, but does not enable local interrupts.
   `u_audio_iso_complete()` therefore runs in hard-IRQ context. It calculates
   packet length (including 64-bit divisions), copies approximately 96 bytes
   at 48 kHz mono S16/1 ms, updates the ring pointer, and requeues the USB
   request. Every 1,200 samples (25 ms in the recorded hw_params), it also
   calls `snd_pcm_period_elapsed()`. That path updates PCM state and can wake
   the bridge. There is no measured duration for these operations, and no
   demonstrated long-running loop in this active completion path.

3. UVC packet encoding runs in the video pump workqueue, with its queue lock
   and interrupts disabled around header generation and the payload copy.
   A request contains up to 2,048 bytes, not a whole uncompressed camera frame.
   Completion callbacks enqueue the next ready packet or a zero-length
   request. DWC2 starts the next queued transfer after the callback returns.
   Thus the stream still requires software servicing every 125 us between
   camera frames, and callback duration affects the rearm deadline.

4. The built configuration has `CONFIG_HZ_1000=y`,
   `CONFIG_PREEMPT_VOLUNTARY=y`, and **no** `CONFIG_IRQ_TIME_ACCOUNTING` or
   `CONFIG_VIRT_CPU_ACCOUNTING_GEN`. Aggregate busy time is useful, but the
   sampled process/thread CPU values cannot isolate interrupt cost. Neither
   the bridge's roughly 3% CPU nor a video thread's CPU share establishes
   which operation delayed the USB controller.

## Specific hypothesis to investigate, not an established cause

The target records audio interval=8 (bInterval=4) and buffer DMA, with
descriptor DMA and service-interval mode disabled. The code advances the
audio software target by eight microframes but starts the next request
immediately. For interval > 1, it sets the endpoint parity at initial NAK
synchronization and leaves that parity unchanged on subsequent requests.
An incomplete-IN event before the software target only clears the global
interrupt; the future audio endpoint remains enabled.

This could generate incomplete-IN interrupts in the intervening microframes
while the controller waits for the host's next audio poll. It is a concrete
candidate for the excess USB interrupt activity, distinct from the tiny
audio payload's bus bandwidth or the ALSA bridge's userspace CPU use.
The existing counters record **retired requests**, not global incomplete-IN
interrupts or their cost. Zero active audio misses therefore does not rule
this out. Conversely, 12,810 aggregate IRQ/s does not establish it: interrupt
sources can coalesce, and their individual counts were not captured.

Related primary references:

- [ST's Synopsys OTG training, interrupt definitions](https://www.st.com/resource/en/product_training/STM32MP1-Peripheral-USB_On-The-Go_Full_and_HighSpeed_interface_OTG.pdf)
  describes incomplete-IN as an unfinished isochronous IN endpoint in the
  current frame. This is a related integration, not proof of BCM2835 timing.
- [TinyUSB 0.20.0 changes](https://docs.tinyusb.org/en/latest/changelog/0.20.0.html)
  includes a DWC2 fix for bInterval > 2 using incomplete-IN handling.
  Its transfer retry strategy is not a drop-in Linux fix and does not prove
  this Pi's failures have the same cause.

Do not change audio interval to 1 based on this hypothesis: that also increases
audio completions from 1,000 to 8,000/s and could make CPU pressure worse.
Do not equate a synthetic interrupt schedule with measured controller timing.

## Evidence boundary

Existing hardware results still establish 26.409 -> 19.487 -> 26.464 fps
mic off/on/off, 457 damaged JPEGs during mic-on, 682 target payload misses,
and roughly 94% busy CPU during combined capture. They do not identify the
initiating deadline failure. The mic's acoustic delay is still unmeasured.

The missing discriminator is global interrupt causes and service duration,
plus the live frame/endpoint state when a transfer is armed and when the
incomplete handler decides to disable it. The current log-readback addition
only retrieves existing diagnostics; it does not add those measurements.
Another flash of that image alone would not settle this hypothesis.
