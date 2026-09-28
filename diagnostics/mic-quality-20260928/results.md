# Microphone quality investigation — 2026-09-28

User reports poor subjective microphone quality. Asked what it sounds like and
which app; no answer yet. Prior timestamp continuity never established sound
quality or acoustic latency. Do not call the audio issue solved.

Analyzed the existing 107.157-second FFmpeg WAV from the combined shutter-image
capture, without opening devices or playing sound. 48kHz mono S16: RMS -38.292dBFS,
peak -15.134dBFS, zero clipped samples, mean -0.867 sample units, largest adjacent
sample step603. No duplicate aligned10ms sample blocks. These checks do not rule
out other distortion or USB loss; FFmpeg has known missing samples vs its PTS.

51 Hann-windowed8192point spectral snapshots excluding first5seconds attribute
99.75% power to below80Hz. Independent FFmpeg80Hz high-pass analysis of seconds5–35
measures -64.352dBFS RMS. Slow baseline movement dominates this ambient recording.
This is a lead, not proof of the reported problem: no known speech/stimulus,
no calibrated acoustic conditions, no measured SNR or frequency response. Possible
acoustic/mechanical or electronics/processing origins are not distinguished.
No gain/filter change applied. Adding gain now could amplify unwanted low-frequency
content. No causal diagnosis or new firmware justified yet.

Source route selects left I2S slot at unity gain, hardwareS32_LE stereo converted
to monoS16_LE48kHz for UAC2. DT declares I2S two32-bit slots, Pi clock master.
Supervisor runs alsaloop50ms nominal latency. These source settings are consistent
with intended routing but do not independently verify actual mic wiring or bits.
No ALSA XRUN/underrun errors found in the saved target log. USB diagnosis from prior
turn still stands for throughput, not subjective microphone quality.

Next useful evidence is symptom/app description and a controlled native PCM speech
recording outside calling-app processing. Do not demand a reflash or card extraction.

## Follow-up: rasping sound; raw I2S evidence

User describes others hearing "sandpaper coming through the screen" and notes
there is no pre-enclosure audio baseline. Do not infer enclosure causation or
promise DSP will repair it. Calling app remains unspecified.

Recovered prior raw `/private/tmp/pisight-pwm-test/target-I2S.S32`, SHA256
090adf463d5b7c64f7edcff357c7129f3095ad2bdae0e6f9ac6888b230c79fb4, matching original
card-readback notes. 96000 stereoS32 frames, right channel zero. After first0.5s,
left RMS-32.985dBFS, peak-19.966dBFS, zero clipping, all low bytes zero (consistent
with24-bit mic data in32-bit samples). An offline one-pole80Hz highpass lowers
RMS to-67.571dBFS. Thus strong low-frequency content exists in an earlier capture
upstream of ALSA bridge/USB transmission. This does not establish the cause of
rasping or exclude separate downstream problems. Short boot capture with unknown
acoustics and older firmware cannot establish speech quality, SNR, or enclosure
loss. See earlier-raw-i2s-analysis.json. No code/image changes or live recordings.

Next discriminating evidence: direct native PCM speech capture and app-processed
speech comparison with installed mic. Does not require removing enclosure or
reflashing. Filtering low rumble is testable offline but cannot be assumed to
repair harsh distortion or recover acoustically lost information.
