# 50 — A/B Thermal Test Plan

The experiment compares complete enclosures at equal operating conditions.
Both variants may pass, fail, or remain inconclusive. No simulated isolation
ratio is treated as evidence.

## Units and controlled factors

Build five A and five B in one assembly lot using the same parts, pack model,
copper stackup, firmware binary and printing settings. The primary experiment
uses 3.3 V on all ten boards (EDS §4.1). Use F-11 serials ENV-0001…0005 for A,
ENV-0006…0010 for B, paired by offset five, and record
serial, component lot, R6, pack serial/capacity, PCB revision and firmware hash.
The physical pack must fit both cases before this protocol starts.

Run any 3.0 V characterization separately after the primary experiment. Record
rework and analyze matched units before/after; never pool different rails as
five interchangeable samples of a geometry.

## Reference, positioning and uncertainty

Use a calibrated temperature/RH reference with certificate, stated uncertainty
and valid range. The ±0.3 °C system target cannot be verified just by observing
a mean within ±0.3 °C against an uncertain reference.

Place the ten DUTs on a circle of 150 mm radius around the reference, with equal
angular spacing and identical orientation. Nearest-neighbor centres are about
93 mm apart (2 × 150 × sin(18°)); do not also require 100 mm separation and a
100 mm reference distance. Map temperature/RH gradients at all ten positions
before testing; record their contribution to uncertainty. A and B alternate.
Rotate each unit by two positions between five repeated equilibrium/charging
runs, then repeat with A/B swapping adjacent positions. Record the permutation.
If room gradients exceed the error budget, use a controlled chamber or local
references rather than correcting away an unexplained variant effect.

Choose and document the reference, timing and spatial uncertainty budget before
collecting acceptance data. Use conservative total uncertainty U including
certificate, spatial gradient and timestamp mismatch. Guard-band temperature
acceptance with max(abs(DUT − reference)) + U ≤ 0.3 °C over the declared
operating conditions. RH uses the equivalent 3 %RH limit and its own U.
If uncertainty prevents classification, the result is inconclusive.

## Acquisition and radio schedule

Acquisition timestamps describe when the sensor converted, not when MQTT
received the batch. For Tests 1 and 4, sample every five minutes and upload
every fifteen minutes; buffer the samples between uploads. Do not introduce
one-minute MQTT traffic to observe a sleeping device. Read before radio start.
The reference logs at least once per minute, with synchronized UTC times.

For charging and step tests, acquire once per minute into local storage and
upload every fifteen minutes. This deliberate non-default cadence is identical
for A and B and is recorded in the run metadata. Establish a matched baseline
at this cadence before interpreting its charging excursion. Missing samples,
reset events and retransmitted batches remain visible.

## Tests

| Test | Condition and acquisition | Duration / analysis window |
|---|---|---|
| 1 | Battery, normal 5/15-minute cadence | 60-minute settling, then 12 hours |
| 2 | Battery, deliberate 1-minute sampling/upload stress | 60-minute settling, then 4 hours |
| 3 | Qualified enclosed charging, same initial measured state of charge, 1/15-minute cadence | 60-minute battery baseline, then charge through termination and cooldown |
| 4 | Battery, default 5/15-minute cadence | 60-minute settling, then 24 hours |
| 5 | Temperature step, nominal 18 → 26 °C, 1/15-minute cadence | Pre-step equilibrium then 2 hours; do not discard the transient |
| 6 | Humidity step, nominal 40 → 70 %RH, 1/15-minute cadence | Pre-step equilibrium then 2 hours; reference measures actual step |

Test 3 starts only after EDS-9 battery-temperature/charge qualification.
Match charger current, source and pack between variants. Log actual current;
charger power is not a fixed 0.40 W across the run. Continue until the
temperature returns to the predeclared equilibrium band, recording cooldown.

## Immutable records and metrics

CSV samples carry:
`run_id, serial, variant, position, acquired_at_utc, sequence, temperature_c,
humidity_rh, battery_v, rail_v, usb_present, charging, quality, reset_reason,
firmware_sha256, reference_temp_c, reference_rh`.

The run manifest records duty cycle, initial state of charge, reference
certificate/uncertainty, enclosure/pack/PCB identifiers, timestamps, and the
position permutation. Raw logs go to `measurements/thermal/`, never edited.
Retain invalid readings with quality flags; never turn a failed read into zero.
Deduplicate only by (serial, sequence, boot identity), keeping the raw data.

Report per-unit mean bias, maximum absolute error, standard deviation and
coverage. Summarize one result per unit per condition, with five paired A/B
differences; thousands of serially correlated samples are not thousands of
independent devices. Report unit spread and uncertainty, not just a group mean.
Charging excursion uses the matched 1/15-minute baseline. Step response is time
to 63% of the measured reference step from the pre-step baseline; report
insufficient settling or sampling resolution instead of inventing a time constant.

## Ordered decision gate

Apply these steps in order; endpoints belong to exactly one branch.

1. Invalid runs, insufficient coverage or unresolved uncertainty: repeat or
   improve the setup. No winner.
2. If neither variant meets guarded F-01/F-02 limits in normal operation, fix the
   design and repeat. Passing on average does not excuse a failing unit.
3. Reject B if any neck shows cracking, warping or intermittent continuity. A
   may advance only if it independently passes the functional requirements.
4. If exactly one variant passes, advance that variant subject to all other
   requirements and mechanical qualification.
5. If both pass, define D as mean absolute unit bias of A minus that of B in
   Test 4. Use the uncertainty interval for the paired comparison: if entirely
   below 0.15 °C, prefer compact A; if entirely above 0.30 °C, prefer B.
6. If the entire interval lies in [0.15, 0.30] °C, prefer B only when A's
   uncertainty-guarded charging excursion exceeds 1.0 °C. Otherwise prefer A.
   An interval crossing either threshold is inconclusive. A proposed charge
   current change requires repeating the relevant tests on both variants.

A product choice is not permission to fabricate or distribute. Release gates
also require power, firmware, RF, sourcing and mechanical evidence.
