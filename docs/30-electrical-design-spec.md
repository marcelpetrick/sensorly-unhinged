# 30 — Rev 1 Electrical Design Specification (EDS)

Status: **locks the schematic**. Rev A1 / B1 share this document entirely.
Every value below traces to a datasheet section or a calculation shown inline.
Anything not yet decided sits in §10 Open items — it is not silently assumed.

Datasheet sources used:
- ESP32-C6-MINI-1/1U Datasheet **v1.5** (Espressif) — Table 3-1 Pin Definitions, Table 6-8, Fig. 11-1 land pattern
- TPS62840 **SLVSEC6D** (TI) — §6 Pin Functions, Table 1 RSET, §9.2.2 externals
- BQ24072/73/74/75/79 **SLUS810N** (TI) — Table 7-2 EN1/EN2, §7.5 K-factors, §10.2.2
- SHT4x Datasheet v7.x (Sensirion), SHT45-AD1F product page

---

## 1. Rail architecture

```
USB-C VBUS ─┬─ ESD ─ IN ┐
            │           │  BQ24074  power path
            └─ CC1/CC2  │  ┌──────────────┐
                        └──┤ IN       OUT ├──► VSYS ──► TPS62840 ──► +3V0 ──► ESP32-C6
                           │              │                 (buck)      │
              JST-PH ──────┤ BAT      TS  ├── 10k                       ├──► SHT45  (island in B)
              1S LiPo      │ ISET ILIM    │                             └──► LED / pull-ups
                           └──────────────┘
```

| Net | Nominal | Notes |
|---|---|---|
| `VBUS` | 5.0 V | USB-C, sink only |
| `VSYS` | 3.6–5.0 V | BQ24074 `OUT`, power-path output; supplies the buck |
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
| *(reserved)* | IO0, IO1 | 12, 13 | `XTAL_32K_P/N` — **left free** for an optional 32.768 kHz crystal if deep-sleep timing accuracy proves insufficient |
| *(spare)* | IO3, IO4, IO5, IO14, IO18, IO21 | 6, 9, 10, 19, 24, 27 | brought to spare test pads where board area allows |
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
though it introduces no new electrical net. Both layouts use the revised routing
order; A has no neck and does not need this spatial count.

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

SON-8 (DLC), 2 × 2 mm. 1.8–6.5 V in, 750 mA, **60 nA typical operating Iq**
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
| 1 | TS | R7 = **10 kΩ 0402 to GND** — NTC unused in Rev 1 (see §5.2) |
| 2, 3 | BAT | `VBAT` |
| 4 | /CE | `GND` (charging enabled) |
| 5 | EN2 | `VBUS` via R8 = 100 kΩ → with the internal 285 kΩ pull-down gives ≈ 3.7 V = logic high |
| 6 | EN1 | `GND` |
| 7 | /PGOOD | `PG_N` (open drain) + R9 = 100 kΩ pull-up to `+3V0` |
| 8, 17(EP) | VSS | `GND` |
| 9 | /CHG | `CHG_N` (open drain) + R10 = 100 kΩ pull-up to `+3V0` |
| 10, 11 | OUT | `VSYS` |
| 12 | ILIM | R11 (see below) |
| 13 | IN | `VBUS` |
| 14 | TMR | **NC** — default safety timers enabled; grounding this pin disables them (TI SLUS810N, Pin Functions) |
| 15 | ITERM | R12 (see below) |
| 16 | ISET | R13 (see below) |

EN2 = 1, EN1 = 0 selects "input current set by external resistor from ILIM to
VSS" (datasheet Table 7-2). When USB is absent, `VBUS` = 0, EN2 falls to 0 and
the part sits in USB100 mode — harmless, since it is not charging.

### 5.1 Charge current — the most thermally consequential resistor on the board

Datasheet K-factors: K<sub>ISET</sub> = 890 AΩ, K<sub>ILIM</sub> = 1550 AΩ,
K<sub>ITERM</sub> = 0.0300 (ISET mode).

| Ref | Function | Equation | Value | Result |
|---|---|---|---|---|
| R13 | fast charge | R = K<sub>ISET</sub>/I<sub>CHG</sub> = 890/0.25 | **3.57 kΩ 1 %** | I<sub>CHG</sub> = 249 mA |
| R11 | input limit | R = K<sub>ILIM</sub>/I<sub>IN</sub> = 1550/0.5 | **3.09 kΩ 1 %** | I<sub>IN,max</sub> = 502 mA |
| R12 | termination | R = I<sub>TERM</sub>·R13/K<sub>ITERM</sub> = 0.025 × 3570 / 0.03 | **3.01 kΩ 1 %** | I<sub>TERM</sub> ≈ 25 mA (0.1 C) |

*BOM option for the slow build:* R13 = 8.87 kΩ → I<sub>CHG</sub> = 100 mA.

**Dissipation check.** The BQ24074 is a linear charger, so
P = (V<sub>IN</sub> − V<sub>BAT</sub>) × I<sub>CHG</sub>. Worst case is an empty
cell: (5.0 − 3.4) × 0.25 = **0.40 W** in a 3 × 3 mm QFN. Typical mid-charge:
(5.0 − 3.8) × 0.25 = 0.30 W. **This is the largest heat source in the product —
larger than the radio, and unlike the radio it runs for hours.** It is the
reason Variant B exists and the reason `PG_N` is wired to a GPIO: firmware must
flag or suspend environmental reporting while charging (E-08).

At 100 mA the same worst case is 0.16 W. The prototype run will tell us whether
250 mA is acceptable inside the enclosure or whether the series build drops to
100 mA and a longer charge time.

### 5.2 TS pin

Rev 1 uses a bare cell plus a separate protection PCM, so there is no NTC in the
pack. Datasheet: "for applications that do not use the TS function, connect a
10 kΩ fixed resistor from TS" — R7 does exactly that, holding TS mid-range so
charging is always permitted. **This is a Rev-1 simplification with a real
consequence: we lose pack-temperature-based charge inhibit.** Low current and
indoor use do not establish safe pack temperature. This is an unresolved release
blocker, not an accepted safety justification. A two-pin pack connector has no
NTC contact: adding pack sensing requires a connector/wiring design and verified
thermistor network, not simply changing R7 into a pull-up.

[TI SLUS810N](https://www.ti.com/lit/gpn/BQ24074), Pin Functions and Battery Pack
Temperature Monitoring, defines TMR and TS separately. TMR is now left open to
enable the default timers; they do not replace pack-temperature monitoring.
EDS-9 owner: hardware maintainer; close before charging prototypes in an enclosure
by selecting the protected pack, implementing temperature inhibit, and testing
hot/cold, missing-sensor, charge termination and timer behavior. No unattended
charging qualification is claimed.

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

### 7.1 Source-current limitation — open, not automatic USB negotiation

EN2/EN1 select a fixed ILIM mode; the two Rd resistors do not tell firmware how
much current a source permits. R11's 502 mA is nominal, not a guaranteed 500 mA
ceiling including tolerance. The circuit has no implemented attach/configuration
policy for an arbitrary USB host. See [TI SLUS810N, Input Current Limit](https://www.ti.com/lit/gpn/BQ24074).

Until EDS-10 closes, bench power uses a regulated 5 V supply whose documented
current capability exceeds the measured worst-case input limit; a 1 A-capable
bench source is the planning fixture assumption. That does not qualify generic
host-powered charging/debug operation. Test attach, source removal, low-battery
TX, current limiting and VBUS transients. A release design must select a supported
source policy and implement appropriate current control/negotiation, with source
and cable compatibility evidence. Owner: hardware/firmware maintainer; closing
gate: before unrestricted USB use. Do not close this by changing documentation
alone.

---

## 8. Battery connector (J2)

JST-PH 2.0 mm, 2-pin, SMD, right-angle or top-entry per mechanical fit.
**Polarity: pin 1 = `VBAT` (+), pin 2 = `GND` (−).** Silkscreen must print `+`
and `−` next to the pins; a reversed 1S LiPo destroys the charger and can vent
the cell. Cell is a *protected* pack (over-charge, over-discharge, over-current);
the PCB does not provide cell protection and must not be built with an
unprotected cell.

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
| EDS-2 | Exact JST-PH SMD MPN and orientation | after enclosure concept |
| EDS-3 | Exact protected LiPo pack (dimensions, capacity, connector, NTC or not) | after measured energy per upload |
| EDS-4 | Whether 250 mA charging is thermally acceptable in the enclosure | thermal Test 3 |
| EDS-5 | 3.0 V vs 3.3 V — R6 value for the series build | prototype power + RF measurement |
| EDS-6 | Whether the 32.768 kHz crystal on IO0/IO1 is needed | deep-sleep timing drift measurement |
| EDS-7 | Antenna: flush with board edge (Rev 1) vs overhanging the outline | RF test in the finished enclosure |
| EDS-8 | Neck width 3.0 / 3.5 / 5.0 mm for Variant B | first bare-PCB mechanical inspection + Test 1 |
| EDS-9 | Pack-temperature charge inhibit, selected protected pack and timer tests; owner: hardware maintainer | before enclosed battery charging |
| EDS-10 | USB source-current policy/control and worst-case input draw; owner: hardware/firmware maintainer | before unrestricted USB use |

## 11. Review checklist for this spec

- [ ] every ESP32 module pin number re-checked against datasheet v1.5 Table 3-1
- [ ] SHT4x pin 1 orientation re-checked against the Sensirion land pattern
- [ ] BQ24074 EP tied to GND with a via array
- [ ] no strapping pin loaded (IO8, IO9, IO15, MTMS/IO4, MTDI/IO5)
- [ ] every open-drain charger output has exactly one pull-up
- [ ] CC1 and CC2 have separate 5.1 kΩ resistors
- [ ] battery connector polarity printed on silkscreen
- [ ] all four island nets, and only those four, cross the neck at 0.15 mm
