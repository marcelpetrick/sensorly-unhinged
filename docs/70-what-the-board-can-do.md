# 70 — What This Board Can Do

The question behind this document: *once the hardware exists, what do I get by
writing only software?*

The short answer is that the board is a **general-purpose 2.4 GHz wireless node
with a laboratory-grade hygrometer and a battery**, and that the radio silicon
is considerably more capable than the product it was chosen for. Most of the
list below costs firmware and nothing else.

---

## 1. The raw capability surface

What the parts physically give you, before any decisions:

| | |
|---|---|
| **Compute** | RISC-V @160 MHz, 4 MB flash, plus a **separate low-power RISC-V core** that can run while the main core sleeps |
| **Radios (all three, same chip)** | Wi-Fi 6 (802.11ax, 2.4 GHz) · Bluetooth LE 5.3 · **IEEE 802.15.4** |
| **Sense** | ±0.1 °C / ±1.0 %RH, factory calibrated, PTFE filtered, with an on-chip heater |
| **Power** | 1S LiPo, USB-C charge with power path, ~7 µA deep sleep, battery voltage on an ADC |
| **Know its own state** | USB present, charging, battery volts, RSSI, reset reason |
| **Talk to you** | one LED, one button, native USB serial/JTAG, 16 pogo test pads |
| **Grow** | 8 spare GPIOs and the I²C bus brought out to test pads |

---

## 2. Three radios, one board — this is the big one

The ESP32-C6 was chosen for Target Wake Time. What comes with it is that the
*same board, unmodified*, can be any of these depending on what you flash:

| Firmware | What it becomes | Why you'd want it |
|---|---|---|
| **Wi-Fi + MQTT/TLS** | the baseline: talks to Home Assistant, InfluxDB, Grafana, or anything | no extra infrastructure, works today |
| **Matter over Thread** | a native Apple Home / Google Home / Alexa sensor | no custom app, no cloud account, no bridge — it just appears |
| **Zigbee** | a Zigbee2MQTT / deCONZ sensor | joins an existing Zigbee mesh, very low power |
| **BLE sensor / beacon** | broadcasts readings as BLE advertisements | phone reads it directly, no network at all; months of battery |
| **ESP-NOW** | peer-to-peer link to another ESP32 | no router, no association, milliseconds to send, ideal for a shed or garage out of Wi-Fi range |
| **Thread + Wi-Fi at once** | a sensor *and* a Thread border router | one node covers both worlds |

That is not a hardware roadmap. It is a firmware choice, one build flag deep.
It is also the strongest argument for having spent the extra euro on the C6
rather than the C3 — the C3 can do only the first and the fourth.

**Battery consequence.** Thread and BLE are dramatically cheaper per message
than Wi-Fi, because there is no association, no DHCP and no TLS handshake. If
runtime ever disappoints on Wi-Fi, Matter-over-Thread is the escape hatch, and
it needs no new PCB.

---

## 3. What one sensor measures once you do the arithmetic

The SHT45 reports two numbers. Those two numbers, plus air pressure assumed at
sea level, give you a surprising amount:

- **Dew point** — the temperature at which condensation starts on a surface.
- **Absolute humidity** (g/m³) — the honest measure of "how much water is in
  this air". Unlike RH, it does not change when the room warms up, so it is what
  you compare between two rooms.
- **Vapour pressure deficit** — the number greenhouses and grow tents actually
  control.
- **Mould risk** — surface RH on a cold wall, from indoor dew point and an
  assumed wall temperature. This is the number that tells a German flat owner
  whether to open a window, and it is genuinely useful.
- **Comfort index / "should I ventilate now?"** — comparing indoor absolute
  humidity to an outdoor feed makes airing-out advice correct rather than
  folklore: in winter, cold outdoor air is *drier* even at 90 %RH.
- **Rate of change** — d(T)/dt shows heating cycles, open windows and doors
  opening, without any extra sensor.

The on-chip **heater** is a real instrument, not a footnote: pulse it and watch
the RH recover, and you get a self-check of whether the sensor is still
breathing or has been sealed in by dust.

---

## 4. What the board knows about itself

Every payload can carry, for free:

`battery_v` · `charging` · `usb_present` · `rssi_dbm` · `firmware` ·
`reset_reason` · `uptime` · `wifi_retries` · `queued_samples`

That turns a fleet of twenty into something you can operate: which unit is
about to go flat, which one sits at the edge of coverage, which one rebooted
last night. It also makes the A/B experiment possible at all — `charging` is
what lets us mark readings as thermally suspect.

**A quietly useful trick:** a unit left plugged in reports `usb_present`. When
mains fails, the flag drops and the node keeps running on its own battery — so
the fleet doubles as a **power-outage logger** with timestamps, for free.

---

## 5. The low-power core changes what "always on" means

`SDA`/`SCL` are on IO6/IO7 deliberately: those are the pins the **LP I²C**
peripheral can reach. That means firmware can eventually read the sensor from
the low-power core while the main CPU stays powered down, and only wake the big
core when something is worth reporting.

Concretely, that unlocks:
- **fast sampling, rare transmission** — 10-second resolution on a battery,
  because 10-second sampling no longer means 10-second wakeups;
- **event-driven reporting** — wake the radio only when temperature moves more
  than a threshold, or when dew point crosses a line;
- **min/max/mean between uploads** instead of instantaneous snapshots, which is
  what you actually want from a 15-minute reporting interval.

None of that needs a hardware change. All of it needs firmware.

---

## 6. Local storage: it survives your network

4 MB of flash holds a ring buffer of ≥ 500 measurements (requirement F-08).
With a compact record that is comfortably **days** of history at the default
interval. The router can reboot, the broker can be down, you can move house —
the data queues and drains when the network comes back.

Room enough as well for two OTA slots, so updates are safe and reversible.

---

## 7. The eight spare pins and the exposed I²C bus

Free GPIOs: **IO3, IO4, IO5, IO14, IO18, IO21**, plus **IO0/IO1** held in
reserve for an optional 32.768 kHz crystal. `SDA` and `SCL` are on test pads
TP12/TP13.

That is a real extension port. Without touching the PCB you could hang on:

| Add | Bus | What it turns the node into |
|---|---|---|
| SCD40/SCD41 | I²C | a **CO₂** monitor — the single most useful indoor-air number after temperature |
| LPS22HH / DPS310 | I²C | barometric pressure, and with it altitude and weather trend |
| SGP41 / BME688 | I²C | VOC / air-quality index (on the *bus*, away from our sensor — which is exactly where a heated part belongs) |
| VEML7700 / LTR-303 | I²C | ambient light, occupancy inference, blind automation |
| Reed switch or PIR | GPIO | door/window state, or presence |
| E-paper display | SPI on spare GPIOs | a battery-powered room display |

Note the pattern: **the thing this design deliberately refused to put next to
its own thermometer — a heated gas sensor — it can still support, on a wire,
where the heat belongs.** That was the point of rejecting the BME680 rather
than the point of rejecting air quality.

---

## 8. What it honestly cannot do

Worth being explicit, so nobody plans on it:

- **No display, no sound, no motion sensing** as built.
- **No mains metering, no relay, no actuator.** It observes; it does not switch.
- **No GPS, no cellular, no LoRa.** 2.4 GHz only, indoor range.
- **No CO₂, VOC or pressure** without adding a part (§7).
- **No external antenna** — that is the `-1U` module variant and a different
  footprint.
- **Wall-clock time survives a reset but not a flat battery**; there is no
  coin-cell RTC. Time comes from the network on boot.
- **±0.3 °C is a system target, not a promise**, and it is the whole reason
  Variant B exists. Firmware cannot fix a thermal path.
- **It is not certified.** Pre-certified module, personal project, no RED/EMC
  campaign. That is a legal boundary, not a technical one.

---

## 9. A reasonable firmware order

If you want the shortest path from bare board to something useful:

| Stage | What you write | What you get |
|---|---|---|
| 1 | blink, USB console, I²C scan | the board is alive and the sensor answers |
| 2 | SHT45 driver + ADC read | temperature, humidity, battery over serial |
| 3 | deep sleep + RTC wake | measured battery life; the first real number |
| 4 | Wi-Fi + MQTT/TLS | readings in Home Assistant |
| 5 | BLE provisioning + NVS | no hard-coded credentials; a device you can hand to someone |
| 6 | ring buffer + bounded retries | survives the router rebooting |
| 7 | factory-test mode on `TEST_MODE` | twenty units become a production run |
| 8 | OTA | you stop unscrewing enclosures |
| 9 | derived metrics (§3), LP core (§5) | it stops being a thermometer and starts being useful |

Stages 1–4 are a weekend. Stages 5–8 are what turn ten prototypes into twenty
deployable devices, and they are where the effort actually goes.
