## Shutter closure check (2026-09-28)

User physically closed shutter. Host still enumerates iSight camera and iSight
Microphone; plain IOUSB tree confirms iSight connected, and USB diagnostic
readback succeeds. Latest saved target snapshot uptime632.59s still has zero
GPIO26 shutter edge IRQs; only logged shutter state is open. No detected closure
in available evidence; wiring/sensor suspected but not proven. User accepts a
purely physical shutter and does not want this pursued. No source or image change,
no reflash or physical wiring action. Evidence: diagnostics/shutter-closed-20260928.
