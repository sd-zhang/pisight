# PiSight PCM ownership conflict (2026-09-27)

The image starts pigpio 79 with no arguments, before starting the ICS43434
capture. Both pigpio and the microphone driver then use the same PCM/I2S
peripheral and clock. This conflict is established in the source and reproduced
with simulated registers. After the correction, the Pi enumerated and the mic
produced changing samples, but video remains degraded and the user reports mic
latency. The initial native 29.91 fps claim was invalid: it counted repeated
images and actually negotiated 1080p. Verified 720p hashing measures 18–19 fps;
other sessions fall below 1 fps. SD readback now confirms the logger saved data successfully after the correction.

## Code path

1. Buildroot's `package/pigpio/S50pigpio` reads `/etc/default/pigpio`, then
   starts `pigpiod` with `$PIGPIOD_ARGS`. The failed image had no defaults file,
   so it used pigpio's default clock: `PI_CLOCK_PCM`.
2. In the built `pigpio-79/pigpio.c`, initialization calls `initClock(1)`
   (line 8345). The default selects `initPCM`, which clears the receive
   configuration and sets `PCM_CS_TXON` (lines 7794–7842). It also programs the
   PCM clock directly, bypassing the kernel clock driver.
3. `linux-custom/arch/arm/boot/dts/broadcom/bcm283x.dtsi:322` maps I2S at
   bus address `0x7e203000` and assigns `BCM2835_CLOCK_PCM`. This is the same
   block pigpio maps as `PCM_BASE`.
4. In `linux-custom/sound/soc/bcm/bcm2835-i2s.c`,
   `bcm2835_i2s_hw_params()` reads the live control/status register. If TXON
   or RXON is already set, it returns success immediately (lines 347–356),
   assuming another audio stream has configured the shared hardware. Pigpio's
   TXON satisfies that guard, bypassing microphone clock, frame, receive, and
   DMA setup. The status register is marked volatile at lines 797–807, so
   this read is not satisfied by stale regmap cache state.
5. `bcm2835_i2s_shutdown()` disables the PCM block after capture closes
   (lines 725–745). Pigpio's GPIO sampling DMA depends on that same PCM
   FIFO/DREQ. The diagnostic image adds a short capture that closes before
   the continuous microphone bridge starts, introducing this shutdown into
   boot. This is a concrete change in the interaction, but does not by itself
   prove why the host times out assigning a USB address or why log copying
   leaves an empty file.

## Reproduction

`check-pcm-clock.py` extracts the actual `initPWM`, `initPCM`, `initHWClk`,
and `initClock` function bodies and constants from the built pigpio source.
It runs them against simulated peripheral registers and applies the actual
I2S driver's early-return guard. Only register storage and delays are mocked;
there is no simulation of DMA transfers, USB, SD I/O, or the full driver.

Run with the existing Docker build volume mounted at `/work`:

```sh
python3 check-pcm-clock.py /work/buildroot/output/build default
# exit 1:
# pigpio clock=PCM; PCM_CS=0x0200020d PCM_RXC=0x00000000 PCM_MODE=0x00002400
# I2S hw_params guard: SKIPS microphone setup
# FAIL: GPIO startup claims microphone peripheral

python3 check-pcm-clock.py /work/buildroot/output/build pwm
# exit 0:
# pigpio clock=PWM; PCM_CS=0x00000000 PCM_RXC=0x00000000 PCM_MODE=0x00000000
# I2S hw_params guard: continues setup
# PASS: GPIO startup leaves PCM registers and clock untouched
```

## Correction and image verification

Added `board/raspberrypizero/rootfs-overlay/etc/default/pigpio` containing
`PIGPIOD_ARGS="-t 0"`. This selects PWM for GPIO sampling. The camera's GPIO
code and logo script use ordinary reads/writes and alerts, not pigpio waveform
output. Waveform output must remain unused because it would initialize the
secondary clock, which is PCM with this selection.

The rebuild completed successfully. Extracting the old and new SquashFS
filesystems and comparing file content, modes, and symlink targets showed
exactly one changed/added file: `etc/default/pigpio`. Running the packaged
`S50pigpio` script with only the daemon launcher intercepted produced
`start-stop-daemon -S -q -x /usr/bin/pigpiod -- -t 0`.

New image: `sdcard-pcm-clock-fix.img`, 41,386,496 bytes.
SHA-256: `616309cfa2851419181469294f5c116760bdcc3a1bca4ab3ae3aed657b05c87e`.
The exported checksum matches the Linux build artifact. The microphone and
diagnostic scripts remain enabled. Following the user's next connection,
host capture produced usable audio samples, but subsequent frame hashing
disproved the initial camera recovery claim. See `../DEBUGGING_NOTES.md` and
`pcm-clock-host-results.json` for corrected results and limitations.
No SD files were edited by the agent during this investigation.

## Subsequent target log readback

The card's log and two-second I2S capture were copied read-only and checksummed
on 2026-09-27. Log: `target-pcm-clock.log` (ignored local artifact). The raw
left channel has 80,877 distinct S32 values across 96,000 frames; the unused
right channel is zero. The log confirms hardware MJPEG selection, repeated
idle-host microphone overruns, a full 9,600-sample gadget playback buffer with
hardware pointer zero, and UVC -61 errors. Logging ended at 88 seconds, before
the later severe reopen stalls. See `../DEBUGGING_NOTES.md` for the UVC error
classification correction and the limits of the audio evidence.
