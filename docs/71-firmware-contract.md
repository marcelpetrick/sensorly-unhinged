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

## Required executable acceptance cases

Measure-before-radio ordering; sensor timeout/CRC failure; flash write power
loss; 501 queued records; duplicate/missing MQTT acknowledgement; AP and broker
outages; bad broker certificate/hostname; expired provisioning; unauthorized OTA;
brownout during OTA; rollback; button factory reset; USB-present cooldown; deep
sleep timing and energy; battery ADC calibration; fixture PASS/FAIL records.

The divider's Thevenin resistance is 1.1 MΩ with 100 nF: RC = 110 ms. A 20 ms
delay is not startup settling. Wait at least 5 RC (550 ms, an engineering settling
target) after first energization, then verify ADC acquisition and calibration
against an external meter across the selected pack range. The divider remains
powered during normal deep sleep; repeated wakeups need not repeat startup delay
unless discharge or power switching occurred.
