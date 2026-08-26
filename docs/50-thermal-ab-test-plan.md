# 50 — A/B Thermal Test Plan

The prototype batch is an experiment, not a first production run. This document
defines the experiment before the boards exist, so the result cannot be chosen
after the fact.

## Hypothesis

> **H1** — In an enclosure, at the same duty cycle, Variant B's reported
> temperature is closer to true ambient than Variant A's, and the difference is
> larger than the unit-to-unit spread within each group.

**H0** — the difference between the A group and the B group is not distinguishable
from the spread within the groups.

Rejecting H1 is a legitimate and useful outcome: it would mean A's compactness
is free, and we ship A.

## Units

5 × A + 5 × B, one assembly lot, one reel of each part. Within each group,
boards 1–3 built at 3.0 V, boards 4–5 at 3.3 V (R6 = 52.3 kΩ / 267 kΩ, EDS §4.1)
so the rail question is answered by the same batch.

Serials `ENV-A01…A05`, `ENV-B01…B05`. Every unit gets an as-built record.

## Reference and conditions

| Item | Requirement |
|---|---|
| Reference instrument | calibrated hygro-thermometer, ≤ ±0.2 °C, certificate on file |
| Reference placement | centre of the array, same height, same airflow, ≤ 100 mm from any DUT |
| Environment | indoor room, doors shut, no direct sun, no HVAC vent within 2 m |
| Array | all 10 units + reference in one plane, 100 mm spacing, same orientation |
| Settling | 60 min at each new condition before recording |
| Logging | 1 sample/min per unit via MQTT, plus reference logged at 1 sample/min |
| Duration | ≥ 12 h per test, spanning at least one night |

**Confounder control.** Rotate the physical positions of the units between runs
(Latin square over 4 runs). Position in the array is a bigger effect than most
people expect, and without rotation it is indistinguishable from variant.

## Tests

| # | Test | Condition | What it isolates |
|---|---|---|---|
| **1** | Deep-sleep equilibrium | normal duty cycle, battery, 12 h | the floor: how good can either variant be |
| **2** | Heavy Wi-Fi | forced upload every 60 s, 4 h | self-heating from the radio |
| **3** | **Charging** | USB connected, cell at 20 %, through to termination | the charger's 0.40 W — the dominant predicted error |
| **4** | Normal duty cycle | 5 min measure / 15 min upload, 24 h | the shipping condition |
| **5** | Temperature step | move array 18 °C → 26 °C room, log 2 h | response time and lag, incl. the -AD1F membrane |
| **6** | Humidity step | 40 %RH → 70 %RH chamber or controlled room, 2 h | RH response and any thermal-bias-driven RH error |

Tests 1–4 run on both A and B simultaneously. Test 3 is the decisive one.

## Recorded per sample

`serial, variant, rail_v, timestamp, temperature_c, humidity_rh, battery_v,
charging, rssi_dbm, firmware, reference_temp_c, reference_rh, position_in_array`

Raw logs land in `measurements/thermal/` as CSV, one file per run, never edited.
Analysis is a script in the same directory, so a number in a report can always be
traced to a row in a file.

## Metrics

For each unit *i* and test *t*:

- **bias** `b(i,t)` = mean(DUT − reference) over the settled window
- **noise** `σ(i,t)` = standard deviation of (DUT − reference)
- **charging excursion** `Δ(i)` = max(DUT − reference) during Test 3 minus `b(i,1)`
- **response time** `τ(i)` = time to 63 % of the step in Test 5

Group statistics: mean and range of `b` within A and within B; the between-group
difference; and the within-group spread. With n = 5 per group we report the
difference with its range, not a p-value — five samples do not support a
significance claim, and pretending otherwise would be worse than saying so.

## Decision gate

| Result | Decision |
|---|---|
| `mean(b_B)` closer to 0 than `mean(b_A)` by **> 0.3 °C**, and the A and B ranges do not overlap | **Adopt B.** Rev 2 is B. |
| Difference **< 0.15 °C**, or the ranges overlap substantially | **Adopt A.** Compactness is free; ship the smaller board. |
| Difference between 0.15 and 0.3 °C | **Adopt B only if** Test 3's charging excursion on A exceeds 1.0 °C. Otherwise A, with the charge current reduced to 100 mA. |
| Either variant fails F-01 (±0.3 °C) in Test 4 | Neither is done. Re-open the enclosure design before choosing. |
| B's neck cracks, warps or shows continuity failures in any unit | **B is disqualified on mechanics**, regardless of thermal result. Go to A, or to Variant C (flex). |

The gate is written down now specifically so that "B is the one I designed more
carefully" cannot become the reason B wins.

## Secondary outputs from the same batch

- **3.0 V vs 3.3 V**: compare energy per upload and RSSI across the two build
  options within each group (closes R-1 / EDS-5).
- **Battery model**: integrate measured current over Test 4 → mAh/day → runtime
  against E-04's >3 months.
- **Charge-current decision**: Test 3 tells us whether 250 mA is acceptable in an
  enclosure or whether the series build drops to 100 mA (closes EDS-4).
- **Neck width**: mechanical inspection of all 5 B boards (closes EDS-8).

## What would make this experiment invalid

Worth stating, because each of these has quietly ruined someone's A/B test:

- **boards from different fabs, or different copper weights.** Inner-plane
  copper weight is the dominant term in Variant A's conduction; 0.5 oz inner
  layers instead of 1 oz would halve it and shrink the effect being measured.
  One fab, one stackup, one order — and record the stackup with the data. See
  `62-fabrication-3-boards.md` §3;
- units built from different part lots, or hand-soldered instead of assembled;
- different enclosure prints (different material, layer height, or infill);
- the reference sitting closer to one group than the other;
- not rotating positions between runs;
- firmware differing between groups in any way, including build date;
- comparing runs taken on different days without a shared reference trace;
- any unit that has been opened, reflowed or touched at the sensor between runs.
