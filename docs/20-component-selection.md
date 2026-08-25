# 20 — Component Selection Trade Study (sensor + MCU)

Status: **decided for Rev 1**, revisit at the Rev 2 gate
Date: 2026-08-25
Supersedes: the provisional picks in `docs/vision.md` §1 / §4 / §5

The vision document *assumed* SHT40 + ESP32-C6-MINI-1. This document tests that
assumption against the alternatives, including the ones explicitly raised in
review: **Bosch BME280/BME680**, other **ESP32 variants**, and **long-term
(multi-year) behaviour** rather than day-one accuracy.

---

## 0. The decision criteria

For *this* product, in priority order:

| # | Criterion | Why it dominates |
|---|---|---|
| 1 | **Temperature accuracy at the die**, incl. self-heating | The whole product exists to report temperature. A ±0.5 °C part makes the entire A/B thermal experiment unmeasurable — our expected A-vs-B difference is of the same order. |
| 2 | **Multi-year drift** | Devices get installed and forgotten. A sensor that is right in week 1 and 4 %RH wrong in year 3 has failed. |
| 3 | **Sleep current & measurement energy** | Target > 3 months on 500–1000 mAh. |
| 4 | **Contamination resistance** | Reflow flux, outgassing plastics, dust. This is the #1 cause of permanent RH offset in the field. |
| 5 | Availability / assembly (JLCPCB-class) | 5 + 5 then 20 units, turnkey. |
| 6 | Size | Matters for A. It is *criterion 6*, not criterion 1. |

Note criterion 1 vs 6: the vision doc's Approach A optimises for size. This
trade study deliberately does not.

---

## 1. Humidity / temperature sensor

### 1.1 Candidates

| Part | T accuracy (typ) | RH accuracy (typ) | T drift | RH drift | Package | Filter option | Notes |
|---|---|---|---|---|---|---|---|
| **Sensirion SHT40** | ±0.2 °C | ±1.8 %RH | <0.04 °C/y (max) | <0.25 %RH/y typ, <0.5 max | DFN 1.5×1.5×0.5 | SHT40-BD1B / SF2 cap | baseline in vision.md |
| **Sensirion SHT45** | ±0.1 °C (5–60 °C) | ±1.0 %RH (20–70 %) | <0.04 °C/y | <0.25 %RH/y | DFN 1.5×1.5×0.5, **pin-compatible** | **SHT45-AD1F = integrated PTFE membrane** | strictly better bin of the same die |
| Sensirion SHT43 | ±0.2 °C | ±1.8 %RH | **<0.01 °C/y** | <0.25 %RH/y | same | — | temperature-stability bin |
| **TI HDC3022** | ±0.1 °C class | **±0.5 %RH** | — | **0.19 %RH long-term** | 2.5×2.5 DEJ | **IP67 PTFE cover integral**, 99.99 % @100 nm | + on-chip *offset error correction* for ageing/contamination |
| Bosch BME280 | **±0.5 °C** (0–65 °C) | ±3 %RH | — | **0.5 %RH/y** | LGA 2.5×2.5×0.93 | none | adds pressure |
| Bosch BME680/688 | ±0.5 °C (+ heater self-heat) | ±3 %RH | — | — | LGA 3.0×3.0 | none | adds VOC gas, needs BSEC blob |
| Aosong AHT20/DHT-class | ±0.3 °C | ±2 %RH | poor/unspecified | poor | — | none | not considered further |

Sources: Sensirion SHT4x datasheet v7.x; SHT45-AD1F product page; TI HDC3022
datasheet; Bosch BST-BME280-DS002.

### 1.2 Why **not** BME280 — the honest version

The BME280 is a fine part and it is everywhere, but it is the wrong part *here*,
for three independent reasons:

1. **±0.5 °C beats our experiment.** The A/B question we are trying to answer is
   "how many tenths of a degree does compactness cost?". With a ±0.5 °C sensor,
   unit-to-unit spread swamps the effect we are measuring. We would need to
   individually calibrate all 10 prototypes against a reference just to run the
   test — which is the cost we were trying to avoid.
2. **±3 %RH nominal, 0.5 %RH/y drift.** After 3 years you are at ±4.5 %RH
   worst-case before enclosure effects. And RH error is *amplified by
   temperature error*: near 90 %RH, 1 °C of thermal bias ≈ 5 %RH of humidity
   error (Sensirion design guide). A part that is worse on *both* axes
   compounds, it does not average out.
3. **Documented field behaviour.** Independent side-by-side testing repeatedly
   reports BME280 units running 1–2 °C hot and, in bad cases, 15 %RH low against
   a bench of other sensors. Some of that is self-heating in the host design —
   which is exactly the failure mode this product is built to avoid — but it
   tells you the part has little margin to give away.

**Pressure is not a reason to pick it.** If barometric pressure is later wanted,
add a dedicated pressure sensor (e.g. LPS22HH/DPS310) on the same I²C bus for
~€1 — do not degrade the primary measurement to get a free secondary one.

**BME680/BME688 are actively disqualified.** The VOC gas element is a hotplate
that runs at 200–400 °C in pulses on the *same die* as the temperature and
humidity elements. Putting a deliberate heater inside a battery-powered
temperature sensor is a contradiction in terms; it also costs mA-scale current
and requires Bosch's closed-source BSEC binary, which conflicts with §3 of
`AGENTS.md`. If air quality is wanted later, it belongs on a separate,
mains-powered node.

### 1.3 The real contest: SHT45-AD1F vs HDC3022

This is close, and both are defensible.

| | **SHT45-AD1F** | **HDC3022** |
|---|---|---|
| RH accuracy | ±1.0 %RH | ±0.5 %RH |
| T accuracy | ±0.1 °C | ±0.1 °C class |
| Long-term RH | <0.25 %RH/y | 0.19 %RH stated |
| Contamination | integrated PTFE membrane | integrated IP67 PTFE cover |
| Ageing correction | on-chip heater (condensation/creep recovery) | **on-chip offset error correction** |
| Size | **1.5×1.5×0.5 mm** | 2.5×2.5 mm |
| Ecosystem | ESP-IDF + Sensirion drivers everywhere; Sensirion publish the definitive PCB/enclosure design guide this whole product is built on | good TI docs, thinner hobby/IDF ecosystem |
| Second source | SHT40/41/43/45 pin-compatible family | HDC3020/3021/3022 family |

**Decision: SHT45-AD1F, with SHT40-AD1B as the drop-in cost-down option and
HDC3022 as the qualified second source.**

Rationale:
- The SHT4x family gives us a **pin-compatible accuracy ladder** (SHT40 →
  SHT43 → SHT45) on *one footprint*. We can populate different bins across the
  10 prototypes without a board change — which is itself useful experimental
  freedom.
- Sensirion's design-in guidance (slots, copper removal, thin necks, chamber
  separation) is the literal basis of Variant B. Using their sensor keeps our
  design and our reference document aligned.
- The **-AD1F filter membrane directly addresses criterion 4**, which is the
  dominant long-term failure mode. This is the single most important upgrade
  over the vision doc's bare SHT40 and it costs about €1.
- HDC3022's ±0.5 %RH and offset-correction are genuinely attractive; it stays on
  the BOM as the alternate and as a candidate for the Rev 2 gate if our
  prototypes show RH creep.

**Change vs. vision.md:** SHT40 (bare) → **SHT45-AD1F (filtered)**. Same
footprint, same I²C address (0x44), same driver, ~€1–2 more per unit,
substantially better on the two criteria that actually matter over 3 years.

### 1.4 Long-term usage measures (independent of part choice)

These are firmware/process items, tracked in the EDS and the firmware backlog:

- **Periodic heater pulse.** SHT4x has an integrated heater specifically for
  removing condensation and reversing RH creep. Schedule a low-duty pulse
  (e.g. 200 mW / 100 ms, once per day, *and always after a >80 %RH excursion*),
  then discard readings for a defined cool-down. Energy cost is negligible;
  it measurably extends calibrated life.
- **No-clean flux, no aqueous wash near the sensor, sensor placed last** in the
  assembly sequence where the vendor allows it; sensor kept in its ESD/dry bag
  until placement. Contamination during *assembly* is the most common cause of
  a permanent offset on an otherwise perfect design.
- **Enclosure materials matter.** No silicone (siloxane poisoning), no
  fresh-printed PLA/ABS outgassing directly against the sensor cavity; bake or
  age printed parts before final assembly. Specify materials in the mechanical
  spec, do not leave it to whoever prints the case.
- **Annual field check.** Each device reports firmware version and a
  `sensor_health` field; a 10-minute side-by-side against a reference at
  deployment gives every unit an as-installed offset record.

---

## 2. MCU / radio

### 2.1 Candidates

| Part | Radio | Deep sleep | Why / why not |
|---|---|---|---|
| **ESP32-C6-MINI-1** | Wi-Fi 6 (11ax) 2.4 GHz, BLE 5.3, **802.15.4** | ~7 µA | **chosen** — see below |
| ESP32-C3-MINI-1 | Wi-Fi 4, BLE 5.0 | ~5 µA | cheaper (~€1 less), same 13.2×16.6 module outline, mature. But no TWT, no Thread/Zigbee/Matter path. |
| ESP32-H2-MINI-1 | **802.15.4 + BLE only, no Wi-Fi** | ~7 µA | *the best battery answer* — Thread/Zigbee avoids the Wi-Fi association cost entirely. Rejected for Rev 1 only because it requires a border router / Zigbee coordinator. Kept as the Variant-C radio option. |
| ESP32-C5 | dual-band 2.4/5 GHz Wi-Fi 6 | higher | 5 GHz is pure cost and power for a 100-byte-per-15-minutes payload. |
| ESP32-S3 | Wi-Fi 4, BLE | ~7 µA | dual-core Xtensa, USB-OTG, more RAM — all irrelevant here, more energy per wake. |
| ESP32 (original) | Wi-Fi 4, BT Classic | ~10 µA + slower boot | older, higher wake energy, no reason. |
| nRF52840 / STM32WB | BLE/Thread | ~1–2 µA | genuinely lower power, but abandons Wi-Fi and the ESP-IDF ecosystem. Out of scope. |

### 2.2 The point almost everyone gets wrong

For a duty-cycled Wi-Fi sensor, **deep-sleep current is not the battery
budget** — the wake-and-connect energy is. A wake cycle spends its energy on
scan → auth/assoc → DHCP → TLS handshake → publish, and that is *seconds* of
tens-to-hundreds of mA. 5 µA vs 7 µA of sleep current is noise by comparison.

That reframes the C3-vs-C6 question completely:

- **C3 wins on sleep current and price. It loses on the thing that matters.**
- **C6 supports 802.11ax Target Wake Time (TWT)**, which lets the node stay
  *logically associated* and wake only in negotiated slots — eliminating the
  20–50 ms association handshake and the DHCP round trip on every single upload.
  Reported real-world idle drain improvements are in the tens of percent.
- TWT requires a Wi-Fi 6 AP. **If the deployment AP is not Wi-Fi 6, C6 degrades
  gracefully to exactly the C3 behaviour** — we lose nothing but the €1.

So the C6 is bought as an *option on a better power mode*, plus an option on
Thread/Matter, for about one euro. On a 20-unit run that is €20 total. Take it.

### 2.3 Decision

**ESP32-C6-MINI-1-N4 confirmed** (module, not bare silicon — the module carries
the crystal, RF matching, antenna and an existing RED/CE type examination, which
removes the single largest RF risk from a 20-unit project).

Firmware must implement both paths and *measure* them on the prototypes:
1. classic deep-sleep + reconnect (baseline, always works),
2. TWT-assisted (used when the AP negotiates it).

That measurement is a Rev-1 prototype deliverable, not an assumption.

---

## 3. Summary of changes to the vision baseline

| Item | vision.md | This study | Impact |
|---|---|---|---|
| Sensor | SHT40 (bare) | **SHT45-AD1F** (filtered, ±0.1 °C / ±1.0 %RH) | same footprint & driver; +~€1.5; large long-term gain |
| Sensor 2nd source | — | **HDC3022** (alt footprint on B only, see EDS) | risk removed |
| BME280/680 | not considered | **rejected, with reasons** | avoids a common default |
| MCU | ESP32-C6-MINI-1 | **confirmed**, with the reasoning corrected (TWT, not sleep µA) | firmware must test TWT |
| MCU fallback | — | C3-MINI-1 pin-strategy noted; H2 as Variant-C | supply-chain resilience |
| Long-term care | contamination noted | heater schedule, material rules, assembly rules, health field | multi-year fitness |

---

## 4. Open questions this study did **not** close

| # | Question | Closes at |
|---|---|---|
| CS-1 | SHT45-AD1F vs SHT40-AD1B for the *final 20* — is ±1.0 %RH worth €1.5/unit at series scale? | Rev 2 gate, using prototype data |
| CS-2 | JLCPCB/LCSC stock + price for SHT45-AD1F and ESP32-C6-MINI-1-N4 at 10 and 20 pcs | before prototype order |
| CS-3 | Does the -AD1F membrane change the required vent geometry / response time? | mechanical design, verified in Test 5/6 |
| CS-4 | Is TWT actually available on the deployment APs? | firmware bring-up |

Sources:
[SHT4x datasheet](https://sensirion.com/resource/datasheet/sht4x) ·
[SHT45-AD1F](https://sensirion.com/products/catalog/SHT45-AD1F) ·
[HDC3022](https://www.ti.com/product/HDC3022) ·
[BME280 datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf) ·
[field sensor comparison](https://olegtarasov.me/environmental-sensors/) ·
[ESP32-C6 TWT vs deep sleep](https://industrialmonitordirect.com/blogs/knowledgebase/esp32-c6-wi-fi-6-twt-power-saving-vs-deep-sleep-analysis)
