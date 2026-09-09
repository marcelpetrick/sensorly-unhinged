# 71 — Firmware implementation and acceptance contract

**Not implemented.** There is no ESP-IDF application in this repository yet.
The hardware build must not report F-03…F-12 as passing. This contract defines
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

## USB input-current state machine

Charging is separately fail-safe. `CHARGE_ENABLE` is IO18 and drives Q1's gate;
external R7 holds the gate low at reset. Separate R18 pulls BQ24074 `/CE` to
VBUS, so charging is disabled before the MCU rail exists. After `PG_N` asserts,
sample `PACK_TS` on IO3/ADC1_CH3 repeatedly,
convert using the Semitec 103AT-2 curve and the measured BQ24074 TS bias, and
drive `CHARGE_ENABLE` high only when the entire uncertainty interval lies inside the pack
drawing's 0–45 °C charge range. Release CE immediately on out-of-range,
implausible/open/short readings, ADC error, stale sample, watchdog warning,
suspend or loss of VBUS; clearing the GPIO turns Q1 off and releases CE high.
Thresholds and hysteresis are generated from reviewed
calibration constants, not raw ADC magic numbers. Until this code and its tests
exist, the board must remain in its default charging-disabled state.

`USB_ISEL` is IO21 and drives BQ24074 EN1. Configure it as an input/high-Z or
drive it low from the first startup instruction; the external 100 kΩ pull-down
then guarantees USB100. Drive it high only from the native USB stack's
**configured** callback. Clear it before acknowledging suspend,
deconfiguration or detach, and on every USB-stack error path. A charge-only
adapter never configures the USB device and therefore remains at 100 mA.

Do not infer source current from `PG_N`, VBUS voltage or the Type-C Rd resistors.
They establish presence/attachment, not host configuration. Do not start Wi-Fi
from USB100 with a missing or deeply depleted pack; report a power-policy fault
and remain in bounded low-power/debug operation. Persist no “500 mA allowed”
state across reset. Telemetry and factory output must expose the selected
USB100/USB500 state alongside USB-present and charging state.

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
