# 00 — Master Plan (distilled)

One page. Everything else in `docs/` is detail hanging off this.

## The product

A battery-powered indoor temperature/humidity node: ESP32-C6 + SHT45, USB-C
charged 1S LiPo, deep-sleep duty cycled, MQTT/TLS telemetry, BLE provisioning,
3D-printed enclosure. Target: >3 months per charge, ±0.3 °C / ±3 %RH **as a
finished product in its case** — not as a datasheet number.

## The central bet

> One electrical platform. Two physical implementations. Decide by measurement.

**Variant A — Compact.** Everything on ~30 × 34 mm. Smallest possible node.
**Variant B — Thermally isolated.** ~28 × 48 mm, the sensor sits on a milled
tongue joined by a narrow FR-4 neck with four thin traces and *no* inner-layer
copper; the enclosure splits into a sensor chamber and an electronics chamber.

Both share schematic, netlist, BOM and firmware. Build 5 + 5, put them side by
side, measure the systematic offset, then pick. Prior expectation: B wins with
~75 % probability — but the point is that we will have the data.

## Phase plan and gates

| Phase | Work | Deliverable | Gate |
|---|---|---|---|
| **0** | Requirements | `10-requirements.md` | targets agreed |
| **1** | Component selection | `20-component-selection.md` | ✅ done |
| **2** | Electrical design spec | `30-electrical-design-spec.md` | every value has a source |
| **3** | Schematic (shared) | `hardware/schematic/` | ERC clean, review checklist signed |
| **4** | Libraries | verified symbols/footprints | pin-1, rotation, land pattern checked vs datasheet |
| **5** | Floorplans A + B | `40-`/`41-floorplan-*.md`, `boardgen` model | envelopes fit the enclosure concept |
| **6** | Layout A ∥ Layout B | two `.kicad_pcb` | DRC clean, RF + thermal keepouts honoured |
| **7** | Enclosures A + B | `mechanical/` OpenSCAD | vents at the sensor, 15 mm antenna clearance |
| **8** | Production package | `hardware/outputs/rev-a1`, `rev-b1` | gerber/drill/BOM/CPL/STEP, DFM reviewed |
| **9** | Prototype order | 5 × A + 5 × B PCBA | quotes compared, boards on order |
| **10** | Firmware bring-up | ESP-IDF app + factory test | self-test PASS on every board |
| **11** | **A/B thermal experiment** | `50-thermal-ab-test-plan.md` + data | **the decision gate** |
| **12** | Rev 2 | corrected board + enclosure | issues from Rev 1 closed |
| **13** | 20-unit series | serialised, tested, deployed | 20 test records in `measurements/` |

Phases 6 and 7 run **A and B in parallel** — that is the whole point of the
parametric generator in `tools/boardgen/`: both boards are emitted from one
model, so a rule change cannot silently apply to only one variant.

## Schedule (focused part-time)

W1 requirements + parts · W2 schematic + libraries · W3 layout A∥B + enclosure
concept · W4 DRC/DFM + order prototypes · W5–6 firmware, backend, fixture,
printed cases · W6–7 bring-up, power, RF, **thermal A/B** · W8 Rev 2 ·
W9–10 Rev 2 build + verify · W11 freeze · W12–13 build/program/test the 20.

≈ 8–13 weeks clean sheet → tested small series.

## Budget envelope (planning only, not a quote)

Prototype programme (5+5, boards + batteries + cases + accessories):
≈ €300–600 low-cost route, ≈ €500–1100 EU-centric route.
Final 20 units: ≈ €20–45 per finished unit, excluding engineering time and
formal compliance.

## Top risks

| Risk | Mitigation |
|---|---|
| **Thermal bias** (the product-defining risk) | sensor island, thin neck, no inner copper, chamber wall, measure-before-radio, reduced charge current — and Variant B exists precisely to bound it |
| **Charger heat** ≥ radio heat | 100–250 mA charge current, physical separation, charging-state flag in telemetry |
| Battery life | deep sleep + bounded retries + batched uploads + TWT; measured, not assumed |
| RF range in case | module antenna keep-out, no LiPo behind the antenna, range test in the finished enclosure |
| RH contamination | filtered sensor variant, no-clean flux, material rules, heater schedule |
| 20 inconsistent handbuilds | turnkey PCBA, frozen BOM, pogo fixture, factory-test firmware, serial numbers, stored records |

## Non-goals for Rev 1

No rigid-flex, no BGA, no blind/buried vias, no 0201, no custom RF, no
mains power, no display, no injection moulding, no formal RED certification
campaign (module pre-certification + documented assessment only), no
double-sided assembly, no fuel-gauge IC.

## Success criterion

Not "a PCB that works". A platform that can be **rebuilt, re-measured and
improved without losing its design history**. Rev 1 is an experiment. Rev 2 is
an engineering product. The 20-unit run is the first controlled series.
