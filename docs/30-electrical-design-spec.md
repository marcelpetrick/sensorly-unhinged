# 30 — Rev 1 Electrical Design Specification (EDS)

Status: **locks the schematic**. Rev A1 / B1 share this document entirely.
Every value below traces to a datasheet section or a calculation shown inline.
Anything not yet decided sits in §10 Open items — it is not silently assumed.

Datasheet sources used:
- ESP32-C6-MINI-1/1U Datasheet **v1.5** (Espressif) — Table 3-1 Pin Definitions, Table 6-8, Fig. 11-1 land pattern
- TPS62840 **SLVSEC6D** (TI) — §6 Pin Functions, Table 1 RSET, §9.2.2 externals
- BQ24072/73/74/75/79 **SLUS810N** (TI) — Table 7-2 EN1/EN2, §7.5 K-factors, §10.2.2
- SHT4x Datasheet v7.x (Sensirion), SHT45-AD1F product page
- [LP702040 drawing FD_3245_20](https://www.li-polymer-battery.com/wp-content/uploads/2021/09/LP702040-550mAh-1032AT-2Molex-51021-0300.pdf) and [configured-pack page](https://li-polymer-battery.com/3-7v-rechargeable-li-polymer-battery-lp702040-550mah-with-ntc-and-molex-connector/) — selected pack and purchasability
- [Semitec 103AT thermistor data](https://www.semitec-global.com/products/thermistor_at/) — pack NTC family/R-T data
- [Molex 53261 series](https://www.molex.com/en-us/products/series-chart/53261) and drawing 532610271-SD — J2 land pattern and ratings
- [Nexperia 2N7002](https://assets.nexperia.com/documents/data-sheet/2N7002.pdf) and [onsemi 2N7002L](https://www.onsemi.com/pdf/datasheet/2n7002l-d.pdf) — Q1 primary/alternate G-S-D pinout and limits

---

## 1. Rail architecture

```
USB-C VBUS ─┬─ ESD ─ IN ┐
            │           │  BQ24074  power path
            └─ CC1/CC2  │  ┌──────────────┐
                        └──┤ IN       OUT ├──► VSYS ──► TPS62840 ──► +3V0 ──► ESP32-C6
                           │              │                 (buck)      │
 LP702040 + PCM + NTC ─────┤ BAT      TS  ├── pack 10k NTC              ├──► SHT45  (island in B)
              1S LiPo      │ ISET ILIM    │                             └──► LED / pull-ups
                           └──────────────┘
```

| Net | Nominal | Notes |
|---|---|---|
| `VBUS` | 5.0 V | USB-C, sink only |
| `VSYS` | mode/load dependent | BQ24074 `OUT`: battery-fed without USB; do not assume a 3.6 V minimum throughout discharge |
| `VBAT` | 3.0–4.2 V | protected 1S LiPo at `BAT` |
| `+3V0` | **3.30 V baseline** | historical net name retained for both build options; R6 sets actual voltage |
| `GND` | — | single net, solid L2 plane (except the Variant-B neck) |

---

## 2. U1 — ESP32-C6-MINI-1-N4

Module, not bare silicon: carries flash, crystal, RF matching, PCB antenna and
Espressif's RED/CE type examination. 13.20 × 16.60 × 2.40 mm, 53 pads
(48 perimeter + 5 ground), land pattern per datasheet Fig. 11-1.

### 2.1 Pin assignment (locked)

| Net | GPIO | Module pin | Rationale |
|---|---|---|---|
| `SDA` | IO6 | **15** | `LP_I2C_SDA` — lets the LP core read the sensor without waking the HP core (future power option) |
| `SCL` | IO7 | **16** | `LP_I2C_SCL` |
| `VBAT_SENSE` | IO2 | **5** | `ADC1_CH2` |
| `CHG_N` | IO23 | **29** | charger `/CHG`, open-drain, external 100 k pull-up |
| `PG_N` | IO22 | **28** | charger `/PGOOD` — this is the "USB is present" flag required by E-08 |
| `LED_N` | IO19 | **25** | status LED, active low |
| `BTN_PROV` | IO9 | **23** | strapping pin with internal weak pull-up: button low at reset = download mode, low at runtime = start BLE provisioning. One button, two jobs. |
| `USB_DM` | IO12 | **17** | native USB Serial/JTAG |
| `USB_DP` | IO13 | **18** | native USB Serial/JTAG |
| `UART_TX` | TXD0/IO16 | **31** | test pad only (fallback console) |
| `UART_RX` | RXD0/IO17 | **30** | test pad only |
| `TEST_MODE` | IO20 | **26** | test pad; fixture pulls low to enter factory test |
| `USB_ISEL` | IO21 | **27** | charger EN1; 100 kΩ pull-down makes USB100 the reset/fault default; firmware may assert only after USB configuration |
| `CHARGE_ENABLE` | IO18 | **24** | drives Q1 gate; external pull-down defaults low, and Q1 can pull charger `/CE` low only after firmware validates pack temperature |
| `PACK_TS` | IO3 / ADC1_CH3 | **6** | reads the pack's 103AT-2 NTC/charger TS voltage; not a spare GPIO |
| *(reserved)* | IO0, IO1 | 12, 13 | `XTAL_32K_P/N` — **left free** for an optional 32.768 kHz crystal if deep-sleep timing accuracy proves insufficient |
| *(spare)* | IO4, IO5, IO14 | 9, 10, 19 | available for later use |
| **NC** | IO8, IO15 | 22, 20 | strapping pins (boot-mode / JTAG-select) — deliberately unconnected |
| `+3V0` | 3V3 | 3 | |
| `EN` | EN | 8 | see §2.2 |
| `GND` | GND | 1, 2, 11, 14, 36–53 | all tied, all via-stitched |

**Deliberate choices to note in review:**
- USB D+/D− *are* connected (the vision document left this optional). The native
  USB Serial/JTAG on the C6 removes any need for a UART bridge IC, makes
  bring-up and debugging vastly easier, and costs two traces plus one ESD array.
  Production programming still uses the pogo fixture.
- IO8 and IO15 are left NC rather than used as spares: both are latched
  strapping pins, and an unexpected external load on them is a classic
  "boots on the bench, not in the enclosure" failure.

### 2.2 Support circuitry

| Ref | Value | Purpose / source |
|---|---|---|
| C1 | 22 µF / 6.3 V X5R 0805 | bulk at supply entrance. Espressif requires ≥ 10 µF; TX peaks reach ~382 mA (datasheet §6.4) |
| C2 | 100 nF / 16 V X7R 0402 | HF decoupling, at pin 3 |
| C3 | 1 µF / 16 V X7R 0402 | mid-frequency decoupling |
| R1 | 10 kΩ 0402 | EN pull-up to +3V0 |
| C4 | 1 µF 0402 | EN RC delay (≈10 ms with R1) — "do not leave EN floating" (datasheet Table 3-1) |
| SW1 | SMD tactile, 3.5 × 2.9 mm | `BTN_PROV` → GND, no external pull-up needed (internal weak PU) |
| C5 | 100 nF 0402 | SW1 debounce |
| D1 | LED 0603, green | status |
| R2 | 3.3 kΩ 0402 | LED series — ~0.5 mA at 3.0 V; the LED is a diagnostic, not a lamp |

Active-low current path: `+3V0 → R2.1 → R2.2 → D1.2 (A) → D1.1 (K)
→ U1.25 (LED_N)`. Pin names are verified against the vendored KiCad LED
symbol and LED_0603 footprint; their geometry and rotation are unchanged.
`make test` guards this path and charger timer wiring for both variants.

---

## 3. U2 — SHT45-AD1F (environmental sensor)

DFN-4, 1.5 × 1.5 × 0.5 mm, no central pad. I²C address **0x44**.

| Symbol pin | Name | Net |
|---|---|---|
| 1 | SDA | `SDA` |
| 2 | SCL | `SCL` |
| 3 | VDD | `+3V0` |
| 4 | VSS | `GND` |

| Ref | Value | Notes |
|---|---|---|
| C6 | 100 nF 0402 | VDD decoupling, placed **on the island** immediately at pin 3 — the only passive allowed there |
| R3, R4 | 10 kΩ 0402 | SDA/SCL pull-ups to +3V0 — **placed on the main board, never on the island** (§3.1) |

### 3.1 Sensor-island electrical rules (apply to both variants; mandatory for B)

1. Exactly **four** nets cross to the sensor: `+3V0`, `GND`, `SDA`, `SCL`.
2. Those four traces are **0.15 mm** wide across the neck and are the *only*
   copper there. No pour, no plane, no stitching vias, no thermal vias.
3. Inner layers L2 and L3 carry **no copper at all** across the neck.
4. `GND` reaches the sensor as a trace, not as a plane. The sensor's ground is
   a stub of the main plane, deliberately high-impedance thermally.
5. No LED, regulator, charger, inductor or battery within the island.
6. Pull-ups sit on the main board so their (small) dissipation stays there.

The B spatial DRC rules name these four nets explicitly, including supply and
ground, and enforce 0.15 mm on every track entering the island rule area.
Membership in the broad Power net class does not permit VBAT/VBUS/VSYS there.
The spatial width rule follows generic width defaults so it takes precedence.
KiCad expression semantics: [custom rules](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom_design_rules).
The generator also counts conductors through successive neck cross-sections:
one trace per named net, all on F.Cu at 0.15 mm. C6 must connect locally on B's
island; a second ground detour through the neck is a thermal-rule failure even
though it introduces no new electrical net. B routes the ground tap before its
supply feed and searches for plane access just above the neck, always excluding
the neck from via placement. These search seeds are geometry assumptions, not
fixed electrical values. A has no neck and retains its existing routing order
and fan-out. Both variants retain the same circuit and netlist.

**Why trace width is the primary lever** — first-order conduction through the
Variant-B neck (3.5 mm wide × 8.0 mm long × 1.6 mm FR-4, four 0.15 mm traces in
35 µm copper), using k(FR-4) ≈ 0.3 W/m·K and k(Cu) = 385 W/m·K:

| Path | Conductance |
|---|---|
| FR-4 bridge | 0.3 × (3.5e-3 × 1.6e-3) / 8e-3 = **0.21 mW/K** |
| 4 × copper trace | 4 × 385 × (0.15e-3 × 35e-6) / 8e-3 = **1.01 mW/K** |
| **Total neck** | **≈ 1.2 mW/K** |

The four hair-thin traces conduct **five times more heat than the entire FR-4
bridge**. Widening them to 0.3 mm would double total neck conduction. This is
the single most important number in the Variant-B design, and it is why §3.1.2
is a hard rule rather than a preference. (First-order estimate, 1-D conduction,
no convection along the neck — to be validated by Test 1–4.)

---

## 4. U3 — TPS62840DLC (system regulator)

SON-8 (DLC), 1.5 × 2.0 mm. 1.8–6.5 V in, 750 mA, **60 nA typical operating Iq**
(datasheet Table: I<sub>Q_VIN</sub> 36 nA typ / I<sub>Q_VOS</sub> 56 nA typ).

| Pin | Name | Net |
|---|---|---|
| 1 | GND | `GND` |
| 2 | VIN | `VSYS` |
| 3 | MODE | `GND` — low = Power-Save Mode, automatic PFM/PWM. Must be terminated. |
| 4 | EN | `EN_REG`, connected to `VSYS` **only through R5**; removing R5 isolates EN for fixture control (never leave the enabled pin floating) |
| 5 | VSET | via R6 to `GND` |
| 6 | STOP | `GND` — normal operation (STOP costs 70 µA, never used here) |
| 7 | SW | `L1` |
| 8 | VOS | `+3V0`, routed directly to C8 with a short trace |

| Ref | Value | Source |
|---|---|---|
| L1 | **2.2 µH**, DFE201612E-2R2M (2.0 × 1.6 × 1.2 mm), DCR ≈ 116 mΩ | datasheet Table 4 |
| C7 | 4.7 µF / 10 V X5R 0603 (input) | "a 4.7-µF ceramic capacitor is required" at VIN |
| C8 | 10 µF / 6.3 V X5R 0603 (output) | datasheet §9.2.2.2 |
| R5 | 0 Ω 0402 | EN tie (a resistor, not a short, so EN can be lifted for current measurement) |
| **R6** | **267 kΩ 1 % 0402 → V<sub>OUT</sub> = 3.3 V baseline** | datasheet Table 1 (E96 nominal) |
| *R6 characterization* | *52.3 kΩ 1 % → V<sub>OUT</sub> = 3.0 V* | controlled characterization only; same table |

### 4.1 Rail margin and controlled characterization

The shared baseline is now **3.3 V**. The [ESP32-C6-MINI-1 datasheet,
Recommended Operating Conditions](https://www.espressif.com/sites/default/files/documentation/esp32-c6-mini-1_datasheet_en.pdf)
specifies 3.0–3.6 V at the module. A nominal 3.0 V leaves no allowance for
regulator error, trace loss or TX transients. R6 = 267 kΩ selects 3.3 V for the
DLC part ([TI SLVSEC6D, Table 1](https://www.ti.com/lit/ds/symlink/tps62840.pdf)).
The historical `+3V0` net name is not a voltage guarantee.

All ten initial units use 267 kΩ for the primary A/B experiment. Only after
baseline testing may matched A/B units be reworked to 52.3 kΩ for a separate
3.0 V characterization run, with new as-built records. This does not qualify
3.0 V for normal use; EDS-5 remains open.

Measure module-pin minimum/maximum voltage during boot, TX and supply switching
across the selected pack's usable discharge range. A buck in 100% duty cannot
maintain its setpoint below dropout. Stop operation before the rail leaves the
module specification; test brownout/recovery and retained records. Required
cutoff depends on measured path loss, pack and transient load, not just nominal
cell voltage. Owner: hardware/firmware maintainer; gate: prototype power test.

---

## 5. U4 — BQ24074RGTR (charger + power path)

VQFN-16 3 × 3 mm with exposed pad (EP → `GND`).

| Pin | Name | Net / value |
|---|---|---|
| 1 | TS | `PACK_TS`: J2.2 → selected pack's **103AT-2 NTC** → J2.1/GND; also U1 ADC1_CH3 (see §5.2) |
| 2, 3 | BAT | `VBAT` |
| 4 | /CE | `CHARGE_EN_N`: R18 = 47 kΩ to `VBUS`, Q1 drain; VBUS disables charging before MCU power-up |
| 5 | EN2 | `GND` — resistor-programmed ILIM mode cannot be selected in normal operation |
| 6 | EN1 | `USB_ISEL` (IO21) + R8 = 100 kΩ to GND |
| 7 | /PGOOD | `PG_N` (open drain) + R9 = 100 kΩ pull-up to `+3V0` |
| 8, 17(EP) | VSS | `GND` |
| 9 | /CHG | `CHG_N` (open drain) + R10 = 100 kΩ pull-up to `+3V0` |
| 10, 11 | OUT | `VSYS` |
| 12 | ILIM | R11 (see below) |
| 13 | IN | `VBUS` |
| 14 | TMR | **NC** — default safety timers enabled; grounding this pin disables them (TI SLUS810N, Pin Functions) |
| 15 | ITERM | R12 (see below) |
| 16 | ISET | R13 (see below) |

EN2 is hard-low. EN1 low selects USB100; EN1 high selects USB500 (datasheet
Table 7-2). R8 keeps EN1 low while the ESP32 is off, reset or high-impedance.
The 500 mA state therefore requires an explicit firmware action after USB
enumeration/configuration; no boot transient can select it.

### 5.1 Charge current — the most thermally consequential resistor on the board

Datasheet K-factors: K<sub>ISET</sub> = 890 AΩ, K<sub>ILIM</sub> = 1550 AΩ,
K<sub>ITERM</sub> = 0.0300 (ISET mode).

| Ref | Function | Equation | Value | Result |
|---|---|---|---|---|
| R13 | fast charge | nominal 890/4420; worst case 975/(4420 × 0.99) | **4.42 kΩ 1 %** | 201 mA nominal, **≤223 mA** worst case |
| R11 | ILIM fallback | nominal 1550/8000; worst case 1720/(8000 × 0.99) | **8.00 kΩ 1 %** | **194 mA nominal, ≤217 mA** if EN2 is reworked high; mode is unreachable as built |
| R12 | termination | nominal 0.0300 × 3010/4420 | **3.01 kΩ 1 %** | ≈20.4 mA nominal, ≤26.1 mA worst case |

The 4.42 kΩ value is selected against E-03's 250 mA ceiling, using the BQ24074
maximum K<sub>ISET</sub> and the resistor's negative tolerance. It is also below
both public pack figures: the product page says 225 mA and drawing FD_3245_20
says 275 mA. The stricter figure governs until the supplier resolves that
conflict in writing. Nominal arithmetic alone is not the safety limit. The
optional 8.87 kΩ slow build remains available for thermal tests.

**Dissipation check.** The BQ24074 is a linear charger, so
P = (V<sub>IN</sub> − V<sub>BAT</sub>) × I<sub>CHG</sub>. Using the bounded
223 mA charge current, (5.0 − 3.4) × 0.223 = **0.357 W** in a 3 × 3 mm QFN.
This is not a
worst-case bound: input/current tolerances, lower cell voltage and power-path
load require separate evaluation. Another point is
(5.0 − 3.8) × 0.223 = 0.268 W. **This is the largest heat source in the product —
larger than the radio, and unlike the radio it runs for hours.** It is the
reason Variant B exists and the reason `PG_N` is wired to a GPIO: firmware must
flag or suspend environmental reporting while charging (E-08).

At 100 mA the same example is 0.16 W. The prototype run will tell us whether
the bounded 223 mA is acceptable inside the enclosure or whether the series build drops to
100 mA and a longer charge time.

### 5.2 Pack temperature and charge qualification

J2.2 connects the selected pack's Semitec 103AT-2 NTC directly to TS and to
U1 ADC1_CH3. The BQ24074 direct-NTC window is approximately 0–50 °C for that
thermistor, while pack drawing FD_3245_20 permits charging only from 0–45 °C.
The charger TS input alone therefore cannot enforce the pack's upper limit.

R18 = 47 kΩ pulls `/CE` directly to VBUS. This reaches a valid high before the
BQ24074's 4.35 V minimum operating input, rather than depending on the later
3 V MCU rail. Q1 (onsemi 2N7002LT1G; G-S-D pins 1-2-3) isolates IO18 from
VBUS. R7 = 100 kΩ holds Q1's gate low at reset or with missing firmware, so Q1
is off and charging is disabled. Firmware may drive `CHARGE_ENABLE` high only
after `PG_N` indicates VBUS and repeated calibrated
`PACK_TS` readings prove the NTC is inside the pack's 0–45 °C charge range with
an uncertainty guard band. It must release CE on out-of-range, implausible,
open/short, ADC, watchdog or timing fault. The BQ24074's own TS hot/cold window
and floating-TMR safety timers remain independent backups.

R18 is checked against TI's approximately 285 kΩ internal CE pull-down:
at the 4.35 V minimum operating input, 4.35 × 285/(285 + 47) = **3.73 V**, above
the 1.4 V high threshold; nominally CE crosses 1.4 V at 1.63 V VBUS, below
charger UVLO. When Q1 is on, R18 asks it to sink only about 5/47 kΩ = **106 µA**.
The onsemi part's maximum 2.5 V gate threshold is specified at 250 µA, so a
3.0 V GPIO drive has margin at this lower drain load. The slow-ramp/startup
waveform is nevertheless part of EDS-9Q because the internal pull-down is only
specified as approximate.

Obtain written confirmation that the shipped pack matches FD_3245_20, then
calculate the firmware thresholds from the Semitec 103AT-2 R/T curve and the
BQ24074 worst-case 72–78 µA TS current. Test cold, hot, sensor-open,
sensor-short, charge termination, safety-timer expiry and recovery on five
packs. Charging in a closed enclosure remains prohibited until that evidence
is linked from `hardware/release-readiness.json`; the circuit implementation
alone is not qualification.

| Ref | Value | Purpose |
|---|---|---|
| C9 | 10 µF / 16 V X5R 0805 | IN bypass (datasheet: 1–10 µF) |
| C10 | 10 µF / 6.3 V X5R 0805 | OUT bypass |
| C11 | 10 µF / 6.3 V X5R 0805 | BAT bypass |
| C12 | 100 nF 0402 | IN HF bypass |

---

## 6. Battery measurement

Requirement F-10, E-05.

| Ref | Value |
|---|---|
| R14 | 2.2 MΩ 1 % 0402, `VBAT` → `VBAT_SENSE` |
| R15 | 2.2 MΩ 1 % 0402, `VBAT_SENSE` → `GND` |
| C13 | 100 nF 0402 at `VBAT_SENSE` |

Divider ratio 0.5: 4.20 V → 2.10 V, comfortably inside ADC1 range with 12 dB
attenuation. Source impedance 1.1 MΩ with C13 gives RC = 110 ms. After first
energization use at least 550 ms (5 RC, engineering target), not 20 ms, and
validate ADC acquisition/calibration against a meter. The continuously powered
divider is already settled on normal deep-sleep wake. See `71-firmware-contract.md`.

**Deviation from the vision document, deliberately.** The vision specified a
*switched* divider (MOSFET or high-side switch) to avoid continuous drain. We
use a permanent divider instead:

- continuous drain = 4.2 V / 4.4 MΩ = **0.95 µA**, i.e. **3.8 % of the 25 µA
  sleep budget** (E-05) and ≈ 8 mAh per *year* against a 500–1000 mAh cell;
- a switched divider costs a MOSFET plus a gate resistor, a GPIO, board area,
  and adds its own off-state leakage and a failure mode where a stuck switch
  reports a flat battery on a full cell;
- the divider sits in the electronics chamber and dissipates 4 µW — thermally
  irrelevant.

Buying 0.95 µA back is not worth three extra parts on a board this size. Recorded
here so the reviewer sees it was a decision, not an oversight.

---

## 7. USB-C (J1) — charge and debug, sink only

| Ref | Part / value | Notes |
|---|---|---|
| J1 | USB-C receptacle, 16-pin SMD, through-hole mounting lugs | mechanical strength is the selection criterion, not pin count |
| R16, R17 | 5.1 kΩ 1 % 0402, CC1→GND, CC2→GND | UFP (sink) advertisement — **two separate resistors, never one shared** |
| U5 | USBLC6-2SC6, SOT-23-6 | ESD on D+/D− and VBUS |
| C14 | 100 nF 0402 | VBUS local |
| — | shield → `GND` | direct tie for Rev 1; document if EMC testing later wants an RC |

D+/D− route to IO13/IO12 as a differential pair, 90 Ω target, kept short and
away from the antenna and the inductor.

### 7.1 Source-current policy — fail-safe USB100, enumerated USB500

The supported policy is explicit:

1. On attach, reset, firmware crash or unconfigured operation, R8 holds EN1 low
   while EN2 is hard-low. The BQ24074 USB100 state limits total input current to
   100 mA maximum (system load plus battery charge).
2. A USB 2.0/3.x data host may be used for charging/debugging. Firmware may set
   `USB_ISEL` high only after the device reaches the USB configured state and
   must clear it on suspend, deconfiguration, detach or USB-stack failure. This
   selects USB500, whose datasheet maximum is 500 mA.
3. USB-C power adapters and charge-only/unknown sources are supported only at
   the 100 mA default because this design does not decode Rp current or charging
   port signatures. They never justify `USB_ISEL=1`.
4. Radio operation from USB with a missing or deeply depleted pack is not
   supported: ESP32 transmit peaks can exceed the 100 mA default. The protected
   battery supplies the transient through the BQ24074 power path. Factory
   battery-less testing uses the declared regulated fixture supply and disables
   radio until USB configuration.

R11 is retained because TI requires ILIM to be terminated, but EN2 low makes its
mode unreachable as assembled. Its 8.00 kΩ value also bounds a deliberate EN2
rework to 217 mA worst case. Qualify with a USB current analyzer: attach/reset,
configuration, suspend/resume, detach, firmware crash, low-battery TX and VBUS
transients on representative USB 2.0 and USB 3.x hosts plus a charge-only source.
The policy and circuit are locked; measured evidence is still required before
the USB release gate closes.

---

## 8. Selected battery and connector (locked architecture)

The shared A/B pack is **LiPol drawing FD_3245_20**, an LP702040 1S1P assembly:
550 mAh minimum / 560 mAh typical, 3.7 V / 2.04 Wh, PCM protected, Semitec
103AT-2 NTC, 45 ± 3 mm AWG-28 UL1571 leads and Molex 51021-0300 connector.
The drawing's maximum assembled envelope is 42 × 20.5 × 7.3 mm. Cavity order is:

| J2 / housing cavity | Wire | Net |
|---:|---|---|
| 1 | black | `GND` (−) |
| 2 | yellow | `TS` / NTC |
| 3 | red | `VBAT` (+) |

J2 is Molex **53261-0371**, the 1.25 mm PicoBlade right-angle SMT header mating
with 51021-0300. The board silk prints `− T +` in cavity order. Its footprint is verified against
Molex drawing 532610271-SD; incoming inspection must continuity-check every pack
before mating because reverse polarity can destroy the charger and vent a cell.

The supplier webpage establishes that this configuration can be purchased in
five-piece prototype quantity and the dated drawing defines the assembly.
Procurement must obtain written lot confirmation, reconcile the page's 225 mA
with the drawing's 275 mA maximum charge current, and supply the applicable
transport test record. No visually similar
two-wire or unprotected LP702040 is an approved substitute. This configured
pack is a single-source prototype risk; a second pack source must be qualified
or explicitly accepted before the 20-unit series.

---

## 9. Design for test (J3 pogo field)

Test pads: **1.5 mm** round exposed copper, **2.54 mm** grid, all on the bottom
side, all within one rectangular region so the fixture is a simple plate.

| # | Pad | Purpose |
|---|---|---|
| 1 | `GND` | fixture ground (two pads, opposite corners) |
| 2 | `VBUS` | inject 5 V without a cable |
| 3 | `VSYS` | power-path output check |
| 4 | `+3V0` | rail check |
| 5 | `VBAT` | battery injection / cell voltage |
| 6 | `EN` | force reset |
| 7 | `BTN_PROV` (IO9) | force download mode |
| 8 | `UART_TX` | console |
| 9 | `UART_RX` | console |
| 10 | `USB_DP` | native USB flashing via fixture |
| 11 | `USB_DM` | native USB flashing via fixture |
| 12 | `SDA` | I²C bring-up / sensor probe |
| 13 | `SCL` | I²C bring-up / sensor probe |
| 14 | `CHG_N` | charger state |
| 15 | `PG_N` | USB-present state |
| 16 | `TEST_MODE` (IO20) | fixture pulls low → factory test firmware |

---

## 10. Open items (this document does **not** close them)

| # | Item | Closing gate |
|---|---|---|
| EDS-1 | Exact USB-C receptacle MPN (JLCPCB basic-part availability drives this) | before prototype order |
| EDS-4 | Whether the bounded 223 mA charging design is thermally acceptable in the enclosure, or the 100 mA option is required | thermal Test 3 |
| EDS-5 | 3.0 V vs 3.3 V — R6 value for the series build | prototype power + RF measurement |
| EDS-6 | Whether the 32.768 kHz crystal on IO0/IO1 is needed | deep-sleep timing drift measurement |
| EDS-7 | Antenna: flush with board edge (Rev 1) vs overhanging the outline | RF test in the finished enclosure |
| EDS-8 | Neck width 3.0 / 3.5 / 5.0 mm for Variant B | first bare-PCB mechanical inspection + Test 1 |
| EDS-9Q | Qualify LP702040 supplier drawing, pack NTC thresholds, protection, timer/fault behavior and assembled retention; owner: hardware maintainer | before enclosed battery charging |
| EDS-10Q | Measure the locked USB100/USB500 policy on representative hosts and fault transitions; owner: hardware/firmware maintainer | before unrestricted USB use |

## 11. Review checklist for this spec

- [ ] every ESP32 module pin number re-checked against datasheet v1.5 Table 3-1
- [ ] SHT4x pin 1 orientation re-checked against the Sensirion land pattern
- [ ] BQ24074 EP tied to GND with a via array
- [ ] no strapping pin loaded (IO8, IO9, IO15, MTMS/IO4, MTDI/IO5)
- [ ] every open-drain charger output has exactly one pull-up
- [ ] CC1 and CC2 have separate 5.1 kΩ resistors
- [ ] battery connector polarity printed on silkscreen
- [ ] all four island nets, and only those four, cross the neck at 0.15 mm
