# 71 — Firmware implementation and acceptance contract

**Partially implemented.** A compiled, radio-disabled engineering application is
described in [bring-up instructions](72-firmware-bringup.md). The hardware build
must not report F-03…F-12 as passing. This contract defines
the work needed to turn the boards into instruments; a contract is not firmware.
Owner: firmware maintainer. Record device-test evidence before the firmware
entry in `hardware/release-readiness.json` can close.

## Acquisition and trustworthy telemetry

Wake → inspect reset cause → acquire sensor with radio stopped → check read/CRC
→ persist sample → optionally connect/upload → stop radio → deep sleep.
Use bounded timeouts and retries. Failure must still reach sleep. Never substitute
zero, a previous value, or an unmarked stale value for a failed sensor read.

Every sample carries schema version, serial (`ENV-00xx` per F-11), variant,
hardware revision, firmware hash, boot identity, monotonic sequence, acquisition
time, clock-valid flag, units, temperature/RH, battery voltage, USB-present and
charging states, and quality flags. Unavailable values are null. Label USB-present
readings thermally suspect even after charging terminates; retain a cooldown
quality state whose duration is established by Test 3. Batch receive time must
never overwrite acquisition time. The consumer can show last-seen age and
quality without inventing accuracy from a numeric payload.

Persist at least 500 measurements in a bounded journal with CRC and recovery
from power loss during writes. Delete only after acknowledgement under the
defined MQTT delivery contract. Duplicate delivery is allowed and deduplicated
by serial/boot/sequence. Declare and count overflow; never silently overwrite
unacknowledged samples. Bound outage radio activity with exponential backoff and
a maximum energy budget, so an absent AP cannot exhaust the battery.

## Provisioning, credentials and updates

BLE provisioning requires a physical button action and per-device proof of
possession, expires after a bounded window, and is disabled in normal sleep.
Explain provisioned, connecting, queued/offline and failed states using brief LED
patterns; leave the LED off in sleep. Factory reset requires a deliberate long
press and removes credentials while preserving the immutable serial.

Use unique device credentials and broker permissions scoped to that serial;
authenticate the broker certificate and hostname. Define trustworthy time
bootstrap before certificate validation; an unset clock must not disable TLS
checks. Never print credentials or commit private keys. Store secrets using the
selected ESP-IDF protection features, and document provisioning/recovery.

OTA accepts only authorized signed images for this hardware, verifies before
activation, keeps a bootable rollback image, and marks the new image healthy
only after self-test. Test interrupted download, interrupted activation, corrupt
and unsigned images, wrong hardware, and a crashing image. Key lifecycle and
irreversible eFuse choices need a reviewed production procedure and hardware
tests; no key-burning operation is part of this review.

## USB and charge supervision

[ADR-001](adr/001-controlled-prototype-power-and-wake.md) supersedes the initial
prototype's assumed USB500 callback and EN2-to-ground wiring. Bring-up drives
EN1/IO21 and EN2/IO14 high (standby), never USB100/USB500/ILIM, with CE disabled.
R8/R20 pull both EN pins to +3V0 while that rail is valid. Before deep sleep the
image releases them to those pull-ups. Rail absent/ramping/collapsing and CPU-hang
behavior still require measurement; no output pull-up overrides an actively
asserted low driver. Battery-less USB startup is unsupported.

The product requirement for USB-C charging is still open. EDS-11/13 must provide
a supported source authorization and complete suspend policy before unrestricted
operation. SOF, serial-port open, PG_N and Type-C Rd are not configured-current
allocation evidence. The pinned fixed-function C6 public driver offers no
configuration callback; USB500 remains prohibited. A controlled lab image may
use USB100 only under a separately reviewed bench-source procedure.

R21 is mandatory DNP and raw PACK_TS is therefore physically isolated from IO3.
Do not populate a zero-ohm link to implement the prior direct ADC connection.
EDS-15 must first define protected sensing across open/short NTC and unpowered
MCU cases, with loading, error and rail-injection bounds. Only then implement
calibrated repeated NTC readings and a charge guard band covering the entire
uncertainty interval inside the pack's 0–45 °C range. Release charge enable on
invalid/open/short/stale samples, ADC failure, suspend and VBUS loss. EDS-12
must bound and measure the watchdog/reset shutdown interval before charging.
The native charger TS window alone does not enforce the pack's upper limit.

Runtime SW1 is now IO1 with an external pull-up, separate from IO9/TP7 download.
Bring-up supports button EXT1 wake experiments; BLE provisioning, factory reset
and their acceptance cases remain product work. A held low button is not armed
for low-level wake, avoiding an immediate wake loop; timer wake remains enabled.

## Required executable acceptance cases

Measure-before-radio ordering; sensor timeout/CRC failure; flash write power
loss; 501 queued records; duplicate/missing MQTT acknowledgement; AP and broker
outages; bad broker certificate/hostname; expired provisioning; unauthorized OTA;
brownout during OTA; rollback; button factory reset; USB-present cooldown; deep
sleep timing and energy; battery ADC calibration; fixture PASS/FAIL records;
USB100 at reset/charge-only attach; USB500 only after configuration; USB100
before suspend/deconfigure/detach; firmware-crash fallback; low-battery TX while
recording source current; CE disabled at reset; valid-temperature charge enable;
hot/cold/open/short/stale-NTC disable and watchdog recovery.

The divider's Thevenin resistance is 1.1 MΩ with 100 nF: RC = 110 ms. A 20 ms
delay is not startup settling. Wait at least 5 RC (550 ms, an engineering settling
target) after first energization, then verify ADC acquisition and calibration
against an external meter across the selected pack range. The divider remains
powered during normal deep sleep; repeated wakeups need not repeat startup delay
unless discharge or power switching occurred.
