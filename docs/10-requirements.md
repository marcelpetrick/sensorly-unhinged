# 10 — Product Requirements v1

Every row is a **target** until a prototype measurement promotes it. Rows marked
🔒 are locked and may only change through an ADR.

## Functional

| ID | Requirement | Target | Verified by |
|---|---|---|---|
| F-01 | Measure air temperature | ±0.3 °C system accuracy, in enclosure, in still air | Test 1 + reference comparison |
| F-02 | Measure relative humidity | ±3 %RH system accuracy, in enclosure | Test 6 |
| F-03 | Measurement interval | 5 min, configurable 1–60 min | firmware config test |
| F-04 | Upload interval | 15 min, configurable | firmware config test |
| F-05 | Connectivity 🔒 | 2.4 GHz Wi-Fi, WPA2/WPA3 | bring-up |
| F-06 | Provisioning 🔒 | BLE (no screen, no keyboard, no AP-mode captive portal) | bring-up |
| F-07 | Telemetry 🔒 | MQTT over TLS, JSON payload | backend integration |
| F-08 | Outage buffering | ≥ 500 measurements retained in flash | firmware failure test |
| F-09 | Firmware update 🔒 | OTA, signed | OTA test |
| F-10 | Battery reporting | battery voltage + charging flag in every payload | bring-up |
| F-11 | Device identity 🔒 | per-device serial `ENV-00xx` + per-device credentials | factory test |
| F-12 | Self-test | factory test mode reporting PASS/FAIL per subsystem | 20 stored test records |

## Electrical / power

| ID | Requirement | Target |
|---|---|---|
| E-01 | Battery 🔒 | 1S LiPo, protected cell, replaceable |
| E-02 | Capacity 🔒 | 550 mAh LP702040 configured pack; PCM + 10 kΩ NTC, three-wire PicoBlade harness |
| E-03 | Charging 🔒 | USB-C, 5 V, **100–250 mA** (deliberately slow — the charger is the largest heat source in the product) |
| E-04 | Runtime | > 3 months per charge at F-03/F-04 defaults |
| E-05 | Deep-sleep system current | < 25 µA total (MCU + regulator Iq + leakage) |
| E-06 | System rail | 3.0 V or 3.3 V — **decided by measurement**, see EDS open item |
| E-07 | Peak supply capability | ≥ 500 mA (module TX peaks ~382 mA) |
| E-08 | Charging-state visibility | firmware must know USB is present and flag readings as thermally suspect |

## Mechanical / thermal

| ID | Requirement | Target |
|---|---|---|
| M-01 | Variant A envelope | PCB ~30 × 34 mm; selected-pack case about 47 × 39 × 19 mm |
| M-02 | Variant B envelope | PCB ~28 × 48 mm incl. 12–20 mm sensor tongue |
| M-03 | Sensor air access 🔒 | vents directly at the sensor, small dead volume |
| M-04 | Antenna clearance 🔒 | ≥ 15 mm free space around the module antenna; no battery, metal or copper behind it |
| M-05 | Thermal isolation (B) 🔒 | two routed slots, narrow FR-4 neck, four thin traces, **no inner-layer copper across the neck**, no thermal vias |
| M-06 | Chamber separation (B) 🔒 | enclosure wall between sensor chamber and electronics chamber |
| M-07 | Battery position 🔒 | not behind the antenna, not under the sensor; 0.5 mm XY clearance and 1.0 mm thickness/swelling allowance |
| M-08 | Enclosure | 3D printed for Rev 1 and Rev 2; battery user-replaceable |

## Manufacturing

| ID | Requirement | Target |
|---|---|---|
| P-01 | PCB 🔒 | 4-layer FR-4, standard thickness, standard finish |
| P-02 | Assembly 🔒 | turnkey SMT, essentially single-sided |
| P-03 | Minimum passive 🔒 | 0402 normal minimum; 0603 where space allows; no 0201 |
| P-04 | No exotic processes 🔒 | no BGA, no blind/buried vias, no rigid-flex, no press-fit |
| P-05 | Test access 🔒 | pogo-compatible test pads for power, programming, I²C and charger status |
| P-06 | Quantities 🔒 | Rev 1: 5 × A + 5 × B. Rev 2/series: 20 |
| P-07 | Revision marking 🔒 | revision string on silkscreen (`HW A1`, `HW B1`, …) |

## Compliance (Germany / EU) — Rev 1 posture

| ID | Requirement |
|---|---|
| C-01 | Use a pre-certified radio module (ESP32-C6-MINI-1) and keep its integration conditions; the finished product still requires its own assessment. |
| C-02 | Document the RED/EMC assessment path; do **not** run a certification campaign for 20 prototypes. |
| C-03 | Li-ion transport rules apply to shipping cells — plan for it, do not discover it. |
| C-04 | WEEE/battery-directive obligations noted for any distribution beyond personal use. |
| C-05 | Security: unique per-device credentials, signed OTA, no shared cloud password across the fleet (CRA direction of travel). |

## Non-goals for Rev 1

Mains power · display · rigid-flex or FPC sensor cable (that is Variant C) ·
air quality / CO₂ / pressure · Matter certification · injection moulding ·
double-sided assembly · fuel-gauge IC · formal RED certification campaign ·
more than 20 units.

## Open questions

| # | Question | Closes at |
|---|---|---|
| R-1 | 3.0 V vs 3.3 V rail | prototype power measurement |
| R-3 | Exact vent geometry / open area | thermal Test 5 response-time data |
| R-4 | TWT available on deployment APs? | firmware bring-up |
| R-5 | Sensor tongue neck width vs mechanical strength | first bare-PCB inspection |
| R-8 | **Board retention.** Only 2 lid hold-down pillars fit on A and 1 on B — no bare board is left. Rev 2 should carry two **nylon** M2 holes; the M-04 objection to fasteners near the antenna is about metal, and nylon is not metal. | Rev 2 |
| R-9 | Qualify the selected pack's controlled drawing, NTC curve, protection behavior, lead routing, swelling space and assembled retention | before enclosed charging |
