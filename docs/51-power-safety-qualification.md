# 51 — Battery and USB power qualification

This protocol supplies the missing physical evidence for EDS-9Q and EDS-10Q.
Passing generated ERC/DRC does not satisfy it. Owner: hardware maintainer, with
firmware maintainer for the USB state-machine cases. Raw logs, instrument IDs,
calibration dates, board/pack serials and photos go under
`measurements/power-safety/<run-id>/`; the release manifest links the reviewed
run summary.

Primary sources are the [BQ24074 datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf),
[LP702040 drawing FD_3245_20](https://www.li-polymer-battery.com/wp-content/uploads/2021/09/LP702040-550mAh-1032AT-2Molex-51021-0300.pdf),
the [configured LP702040 product page](https://li-polymer-battery.com/3-7v-rechargeable-li-polymer-battery-lp702040-550mah-with-ntc-and-molex-connector/),
and the [Molex 53261 series record](https://www.molex.com/en-us/products/series-chart/53261).
Q1 limits and pinout come from the
[onsemi 2N7002L datasheet](https://www.onsemi.com/pdf/datasheet/2n7002l-d.pdf),
with [Nexperia 2N7002](https://assets.nexperia.com/documents/data-sheet/2N7002.pdf)
as the recorded second source.
The supplier page is not a controlled pack drawing; any conflict is resolved in
favor of the signed drawing obtained with the lot, then reviewed as a design
change if it alters the locked interface.

## Stop conditions

Do not charge a pack in either enclosure until the supplier-document, incoming
inspection, TS fault and current-limit stages below pass on the bench. Stop a
test immediately for swelling beyond the controlled drawing, damaged insulation,
unexpected odor/noise, pack voltage or temperature outside the supplier limits,
reversed/unstable current, or failure of a commanded charge suspension. Isolate
the unit using the lab's lithium-battery incident procedure; do not continue to
collect data from a suspect pack.

## Pack and charger qualification

Use at least five production-intent LP702040 assemblies from the intended lot.

| Stage | Method | Acceptance |
|---|---|---|
| Supplier record | Obtain written confirmation that the lot matches FD_3245_20, including 103AT-2, 45 ± 3 mm AWG-28 UL1571 leads, cavity order and applicable transport-test record. Reconcile the web page's 225 mA and drawing's 275 mA charge limits. | Every field is present and the more restrictive unresolved limit is used. |
| Incoming inspection | Photograph and measure every pack; continuity-check cavity 1 to negative, cavity 3 to positive, and cavity 2 only to the NTC. Measure NTC resistance at a recorded room temperature before mating. | Polarity is `1=black/-`, `2=yellow/NTC`, `3=red/+`; maximum envelope is 42 × 20.5 × 7.3 mm and resistance agrees with 103AT-2 data. |
| Geometric fit | Install each pack in printed A and B bases with the production insulation/retention materials. Inspect the 45 ± 3 mm lead path and connector mating/unmating. Close the lid and run the existing interference check plus physical inspection. | No pinch, sharp bend, abrasion, compression or rigid material occupies the 0.5 mm XY / 1.0 mm Z allowance; the pack cannot reach the antenna or sensor chamber. |
| NTC characterization | Stabilize a pack and calibrated reference at multiple temperatures spanning 0–45 °C. Record pack NTC resistance, ADC code and TS voltage. Establish firmware enable/disable guard bands from the 103AT-2 curve, ADC uncertainty and BQ24074's 72–78 µA TS bias before applying charge current. | Firmware permits CE only when the full temperature uncertainty interval is within 0–45 °C on all five packs; charger TS remains an independent wider backup window. |
| TS/firmware faults | With a battery simulator or protected pack at safe state of charge, open and short the NTC conductor separately; inject stale ADC, conversion-error and watchdog paths; then restore it. Record `CHARGE_ENABLE`, CE, BAT current, `/CHG`, `/PGOOD`, TS and VBUS. Include a no-battery cold attach and slow VBUS ramp to verify startup ordering. | R7 holds Q1 off and R18 raises CE with VBUS before charger operation. Every invalid/fault condition turns Q1 off, releases CE and stops charging; no missing firmware or sensor fault can enable charging. |
| Charge current | At safe pack temperatures and declared initial states of charge, log input current, BAT current/voltage and charger/pack temperature in USB100 and enumerated USB500. | Input never exceeds the respective 100 mA / 500 mA datasheet maximum; BAT charge current never exceeds the design's 223 mA worst-case bound. |
| Termination/recharge | Charge every pack through normal termination, observe recharge behavior after controlled discharge, and repeat across the supplier's allowed temperature range. | No limit from the controlled pack drawing is exceeded; termination and recharge are repeatable and `/CHG` agrees with measured current. |
| Safety timers | Use a battery simulator/electronic load to hold precharge and fast-charge conditions; do not abuse a pouch cell to create timeout. TMR remains physically open. | Precharge timeout occurs within 1440–2160 s and fast-charge timeout within 14400–21600 s, the BQ24074 floating-TMR limits. |
| Enclosed charge | Only after all prior stages pass, run one full charge in each finished A/B enclosure while logging charger, pack, sensor and ambient temperature. | No supplier limit or mechanical stop condition is crossed; data are retained for thermal Test 3. |

## USB source-policy qualification

Use a calibrated USB current/voltage analyzer and at least two USB 2.0 hosts,
two USB 3.x hosts (including USB-C where available), and one charge-only USB-C
source. Test with a normally charged pack, the lowest permitted operating pack
voltage, and no pack where the case permits it. The no-pack case keeps radio off.

| Event | Required state and acceptance |
|---|---|
| Cable attach, reset and boot | `USB_ISEL=0`; total input is at or below 100 mA. |
| Before USB configured | `USB_ISEL=0`, including long enumeration and rejected-device cases. |
| Configured by data host | Firmware may set `USB_ISEL=1`; total input remains at or below 500 mA. |
| Suspend, deconfigure and detach | Firmware clears `USB_ISEL` before/at the transition; no retained 500 mA authorization. |
| Charge-only/unknown source | It never reaches configured state, so `USB_ISEL` remains low and input stays at or below 100 mA. |
| Watchdog reset or induced USB-stack crash | External R8 returns EN1 low without firmware; input returns to the USB100 bound. |
| Low-pack radio transmit after configuration | Source remains within 500 mA and the battery safely supplies any power-path supplement current. |
| Missing/depleted pack before configuration | Firmware does not start radio; it reports/records a bounded power-policy fault where possible. |

Capture GPIO, VBUS, input current, VBAT, BAT current, `PG_N`, `CHG_N` and USB
stack state on one time base. A table saying “worked” is not evidence. Any
source-specific workaround becomes a documented supported-source restriction,
not an unrecorded exception.
