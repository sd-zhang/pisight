# Advertised video modes over UVC

Selector 5 on the existing `PiSightSettings1` extension unit lets a future app
choose which resolution presets other applications can see. The host still
negotiates its capture resolution within that advertised list using normal UVC
Probe/Commit. Ordinary capture resolution changes require no reboot.

This selector uses the same 32-byte version-1 request envelope, token, GET_LEN,
GET_INFO and transport validation as [audio/diagnostics](uvc-audio-controls.md).
There is no new app, serial interface or USB endpoint.

## Mode mask

| Bit | Resolution |
|---|---|
| 0 (`1`) | 1280×720 |
| 1 (`2`) | 1920×1080 |
| 2 (`4`) | 1280×960 |

Choose any nonempty subset: masks 1–7. For example, 1 advertises only 720p, 3
advertises 720p and 1080p, and 7 advertises all three (the default). Modes retain
the existing MJPEG format and frame intervals. This changes the advertised
output list, not the sensor's physical capabilities or framing control.

## SET operations

Version at byte 0 is 1, operation at byte 1, bytes 2–3 are zero, and bytes 4–7
contain a nonzero little-endian token. Reserved bytes must all be zero.

| Operation | Meaning | Bytes 8–31 |
|---|---|---|
| 1 | Select modes in RAM | Mask at byte 8; remaining bytes zero |
| 2 | Save selected modes to JSON | All zero |
| 3 | Reset selection in RAM to all three presets | All zero |
| 4 | Save selected modes and soft reboot the Pi | All zero |

Selection does not disrupt streams. Save updates only `.resolutions` in
`/boot/isight.json`, in the table's order, preserving all other fields. The
first selected mode becomes the default frame. Existing custom JSON lists
remain supported at boot; mask zero reports a list not representable by these
presets. Save/reboot is rejected until a valid preset subset is selected.

Operation 4 is the explicit **Apply and restart** action. The asynchronous
writer saves, successfully remounts the boot partition read-only, waits one
second to allow the control transfer to finish, then requests a normal
init-managed software reboot. Save/remount failures prevent that reboot. No
forced reboot or physical unplug is used. USB camera and microphone disappear
during the full boot and return with the selected list. Capture is interrupted;
an application holding the old device may need to reopen it. This implementation
uses a full Pi reboot, not a faster USB-only reconnect.

The future app should offer this action explicitly, close its capture handles,
and wait for rediscovery. Do not resend operation 4 automatically following a
USB timeout: disconnect may already mean it was accepted. After rediscovery,
read the active mask and confirm the advertised descriptors. Tokens/status are
RAM-only and reset on boot. All settings reload from JSON, so save any desired
live audio/camera/diagnostics changes before this action. Unsaved changes and
RAM diagnostic logs are lost on reboot.

## GET response

| Offset | Length | Meaning |
|---|---|---|
| 0 | 1 | Version 1 |
| 1 | 1 | Status: 0 success, 1 invalid, 2 I/O error, 3 writer pending |
| 2 | 1 | Flags below |
| 3 | 1 | Zero |
| 4 | 4 | Last accepted/processed token (LE32) |
| 8 | 1 | Selected mode mask |
| 16 | 1 | Last successfully saved mode mask |
| 24 | 1 | Active advertised mode mask from this boot |
| Other | | Zero |

Flags: bit 1 selection differs from saved mask; bit 2 a writer is pending across
selectors 3–5; bit 3 saved descriptors need a restart. Bit 3 also accounts for
canonicalizing an older list's order or removing duplicates, even if its mask
is unchanged. Custom boot lists report mask zero until a preset is selected.

Serialize requests and poll modestly (for example 5 Hz). While a writer is
pending, SETs on selectors 3–5 are ignored and do not replace its token. The
existing shared nonblocking config lock also serializes camera settings writes.
Operation 4 can disconnect before a final success response; success of its
USB transfer alone does not prove the new modes are active. Failure after the
JSON replacement may leave new settings saved even if status is I/O error.

## Verification boundary

Offline checks exercise payload validation, all seven masks, asynchronous
save/error/busy behavior, existing audio controls, real BusyBox/jq persistence,
boot environment restoration, descriptor selector routing, and save-before-reboot
ordering with a substituted reboot endpoint. They do not prove physical USB
rediscovery, host descriptor caching, or simultaneous capture after reboot.
Those need a hardware check after flashing firmware with selector 5.
