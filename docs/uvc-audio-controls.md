# PiSight audio and diagnostics settings

Firmware capabilities for a future UVC app. There is no new host app, CLI,
web server, serial interface, or USB endpoint. Find the existing extension
unit by its 16-byte GUID `PiSightSettings1`; discover its assigned unit ID.
Selector 1 remains camera settings and selector 2 remains snapshot readback.
Selectors 3 (audio) and 4 (diagnostics) each carry 32 bytes.
Selector 5 configures [advertised video modes and software restart](uvc-video-modes.md).

Use class/interface requests on the VideoControl interface: `wIndex` has the
unit ID in its high byte and interface number in its low byte; `wValue` is
selector shifted left 8. `GET_LEN` returns LE16 value 32, `GET_INFO` returns
3 (GET/SET supported). Use `GET_CUR` (0x81, direction 0xa1) and `SET_CUR`
(0x01, direction 0x21). SET requires exactly 32 bytes. GET accepts 1–32,
but apps should read the full 32. GET_MIN/MAX/RES/DEF are unsupported.

## SET payload, both selectors

All multibyte fields are little-endian; reserved bytes must be zero.

| Offset | Length | Meaning |
|---|---|---|
| 0 | 1 | Version, 1 |
| 1 | 1 | Operation: 1 Apply, 2 Save, 3 Reset defaults |
| 2 | 2 | Reserved |
| 4 | 4 | Nonzero request token selected by app |
| 8 | 8 | Apply values below; all zero for Save or Reset |
| 16 | 16 | Reserved |

Selector 3 Apply: signed LE16 gain at offset 8 in tenths of a dB; LE16
high-pass Hz at 10; LE16 low-pass Hz at 12; bypass boolean byte at 14;
byte 15 zero. Accepted limits:

- Gain −24 to +24 dB, steps of 0.5 dB (wire −240..240, step 5).
- High-pass: 0 disables it; otherwise 20..500 Hz, whole Hz.
- Low-pass: 0 disables it; otherwise 1000..20000 Hz, steps of 100 Hz.
- Bypass: 0 or 1. Bypass disables both filters and gain.

Defaults are 0 dB, 80 Hz high-pass, 8000 Hz low-pass, bypass false.
Filters are second-order Butterworth sections at 48 kHz. Live changes crossfade
over 20 ms without another audio queue. During a fade the latest accepted
request is retained for the next block after the fade ends. With capture closed,
Apply is remembered in RAM and takes effect at the next capture start.
High gain can clip; no compressor, noise suppression, or automatic gain is added.

Selector 4 Apply: offset 8 is diagnostics enabled, 0 or 1; bytes 9–15 zero.
Default is off. Apply changes RAM only. Reset restores defaults in RAM only.

## GET payload

| Offset | Length | Meaning |
|---|---|---|
| 0 | 1 | Version, 1 |
| 1 | 1 | Status: 0 success, 1 invalid request, 2 I/O failure, 3 Save pending |
| 2 | 1 | Flags below |
| 3 | 1 | Reserved, zero |
| 4 | 4 | Most recently processed request token, zero before any request |
| 8 | 8 | Audio requested preset; or diagnostics desired boolean at byte 8 |
| 16 | 8 | Audio last applied preset; or diagnostics saved boolean at byte 16 |
| 24 | 2 | Audio output absolute peak, 0..32768 PCM units |
| 26 | 2 | Reserved |
| 28 | 4 | Audio saturated-sample count since latest capture prepare |

Flags: bit 0 recent audio activity (audio selector only), bit 1 unsaved changes
relative to successful Save/boot settings, bit 2 a Save is pending across
selectors 3–5. Other bits and unused diagnostics bytes are zero. Audio presets use
the same 8-byte layout as SET offsets 8–15. Applied can lag requested while
capture is closed or fading. Peak updates roughly every 100 ms and clipping
counts wrap at 2^32. Activity expires after about two seconds without audio
transfers; meters are stale when inactive and reset on capture prepare.
Separate atomic fields are observations, not a transactionally frozen meter set.

Serialize requests. After SET, GET and match the token and status; USB transport
success alone is not application success. Invalid payloads leave settings intact
and return status 1 with their token (or zero for a too-short payload).
Save captures the current desired setting and writes asynchronously in a child
process, preserving other JSON fields. Poll until bit 2 clears and check status.
While Save is pending, further SETs on selectors 3–5 are ignored; their tokens
are not accepted. Retry only after completion. There is no token deduplication:
avoid repeated Save requests, and use modest GET polling (e.g. 5 Hz).
A failed Save leaves the live setting in RAM and reports status 2. If failure
occurs after replacement, the SD contents may already have changed; status does
not imply rollback. Camera and audio/diagnostics JSON writers share a nonblocking
lock to prevent concurrent updates from overwriting one another.

## Persistence and diagnostics behavior

`/boot/isight.json` stores `audio` and `diagnostics` alongside existing settings:

```json
{
  "audio": {"gain_db": 0, "highpass_hz": 80, "lowpass_hz": 8000, "bypass": false},
  "diagnostics": false
}
```

Existing files without these keys get the defaults. Malformed audio presets
fall back as a whole; only JSON boolean true enables diagnostics. Save persists
the selected category, not both. Normal boot still seeds or repairs a missing or
invalid config file. Live Apply/Reset do not persist changes.

Enabled diagnostics collect a snapshot every 60 seconds into RAM at
`/tmp/PISIGHT.TXT`, capped at 4 MiB (individual appended snapshots capped at
256 KiB). At the limit, the next snapshot starts a fresh log. Disabling prevents
further collection/publication; previous RAM data remains available through
selector 2 until rotation or reboot. Enabling live takes effect by the next
scheduled snapshot. No periodic log copies or raw-capture copies go to SD.

The optional two-second raw I2S boot probe runs only if diagnostics was enabled
at boot. Enabling live does not interrupt microphone capture to rerun it.
Microphone detail snapshots also respect the toggle. Existing USB recovery
counters and basic process/error logs remain in RAM; the 4 MiB cap specifically
covers the downloadable snapshot log, not every process log. No logs survive
power-off unless downloaded by a host. Turning diagnostics off does not change
USB recovery logic or remove counters needed for it.
