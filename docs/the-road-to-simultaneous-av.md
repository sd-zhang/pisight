# The webcam that worked until it became a webcam

A camera that streams video and a microphone that records sound can each look
finished. Put them on the same Pi Zero, open both at once, and the useful test
finally begins.

PiSight already had hardware JPEG encoding. The obvious expensive operation had
been moved off the single ARM1176 core. Yet enabling the microphone could turn
video into a slideshow. At different points the host saw only audio devices,
no camera, nearly constant microphone samples, or a camera whose frame rate
collapsed when recording started. Those were different symptoms, and treating
them as one problem sent the investigation down several unproductive paths.

## First, make the devices real

One failure happened before performance mattered: a legacy audio gadget claimed
the Pi's only USB controller before the intended composite gadget could bind.
Another exposed the wrong audio direction. Fixing enumeration made the camera
and microphone visible, but visibility was not proof that sound was arriving.

The microphone's raw output then pointed toward a less obvious conflict.
pigpio used the PCM peripheral for its clock; the I2S microphone needed that
same peripheral. The resulting register state made the I2S driver skip part of
its setup. Moving pigpio's clock selection to PWM cleared that conflict.

There was also an audio bridge running when nobody was listening. USB playback
was not advancing normally in that state, while a high-priority loop kept
working and building a queue. Starting and stopping the bridge from actual
ALSA capture activity was a better match for what a webcam does.

These fixes were necessary. They were not the end of the frame-rate problem.

## The expensive work nobody asked for

The Zero was spending CPU on work that did not improve the picture. Disabled
libcamera debug messages still paid formatting costs. A GPIO sampling worker
consumed roughly eleven percent of the processor while monitoring a shutter
sensor that did not appear to work on this particular assembly.

Removing that polling and avoiding suppressed log formatting restored useful
headroom. LEDs could follow existing stream events. The shutter, where wired
correctly, could use kernel GPIO edges instead of a permanent sampling worker.
On this unit the user was happy for the shutter to remain purely mechanical.

Video returned close to thirty frames per second with audio active. That was a
real improvement, but occasional corrupt frames remained. CPU pressure and USB
correctness had been overlapping problems.

## A scheduling problem hiding inside recovery

The difficult part lived in the DWC2 USB gadget driver's isochronous scheduling
and recovery. A recovery path could associate an older interrupt event with a
new request and retire video payloads prematurely. Fixes had to preserve queue
ownership, frame wraparound and cancellation; merely making a comparison more
conservative failed offline cases.

Audio endpoint timing mattered too. An endpoint could be enabled before its
intended host polling slot. The final approach used a short timer lead and a
temporary start-of-frame interrupt to arm audio in the intended USB frame. It
did not add a permanent stream of start-of-frame interrupts.

The evidence improved in stages. Some intermediate patches reduced bad events
without restoring acceptable video. The later combination removed the recurring
interrupt storm and the disabled-video-payload failures seen in the earlier
trials. Rare NAK misses remained. Calling every intermediate build “the fix”
would have hidden that distinction.

## The cost of evidence

There was a practical constraint: every new SD image required someone to handle
a tiny card in a physical device. Missing logs were not an excuse to keep
repeating that chore. Diagnostic readback moved onto the existing UVC extension
unit, so logs could be retrieved without adding serial or opening the enclosure.

That path has a cost too. A bulk log download during a later test briefly reduced
video delivery, then normal delivery returned. It did not reproduce the lasting
slowdown associated with earlier serial experiments. The eventual settings app
should request logs after a call or pace the transfer.

Logging itself became optional. Periodic snapshots now live in bounded RAM,
with diagnostics off by default. Toggling it does not make a stream of SD writes;
settings persistence requires an explicit Save. Basic recovery counters remain
available because they are useful for explaining the next failure.

## A baseline worth keeping

The accepted hardware run delivered **29.96 distinct frames per second with the
microphone open**, with six JPEG errors over about two minutes. Native combined
captures had continuous 48 kHz audio timestamps. Live microphone gain, filter
cutoffs and bypass worked through UVC, ready for a future app.

The new audio processing has a measurable price: the microphone process rose from roughly
five to nine percent CPU. Filtering, tuning and meters were deployed together,
so this run does not isolate their individual costs. Total CPU was around seventy-one to seventy-two percent
in mostly active windows. That is headroom, not proof that optimization is over.
Earlier camera micro-optimizations improved isolated benchmarks without showing
a meaningful whole-device gain. The measurements deserved more weight than the
appeal of the optimization.

Hardware encoding still leaves work for the CPU. Sound quality and acoustic
delay need their own measurements. What we have is an accepted simultaneous A/V
baseline with known limits, and diagnostics that can be turned off once they
have done their job.

Numbers and caveats: [accepted hardware report](../diagnostics/capture-audio-settings-20260928/results.md).
The [archived investigation](history/development-log-2026-09.md) preserves the
false starts and intermediate results behind this account.
