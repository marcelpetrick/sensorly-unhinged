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
| `BTN_PROV` | IO1 | **13** | runtime button and C6 EXT1 wake; R19 external pull-up; no boot-strap function |
| `BOOT_N` | IO9 | **23** | independent factory download strap on TP7, no runtime button |
| `USB_D_N` | IO12 | **17** | native USB Serial/JTAG |
| `USB_D_P` | IO13 | **18** | native USB Serial/JTAG |
| `UART_TX` | TXD0/IO16 | **31** | test pad only (fallback console) |
| `UART_RX` | RXD0/IO17 | **30** | test pad only |
| `TEST_MODE` | IO20 | **26** | test pad; fixture pulls low to enter factory test |
| `USB_ISEL` | IO21 | **27** | charger EN1; R8 pull-up to +3V0 selects standby with EN2 high while rail valid |
| `USB_EN2` | IO14 | **19** | charger EN2; R20 pull-up to +3V0; firmware keeps EN1/EN2 high in bring-up |
| `CHARGE_ENABLE` | IO18 | **24** | drives Q1 gate; external pull-down defaults low, and Q1 can pull charger `/CE` low only after firmware validates pack temperature |
| `PACK_TS_SENSE` | IO3 / ADC1_CH3 | **6** | isolated from raw PACK_TS by mandatory DNP R21; not sampled by bring-up |
| *(reserved)* | IO0 | 12 | IO1 is allocated to runtime wake; an external crystal now requires a reviewed pin reassignment (EDS-6) |
| *(spare)* | IO4, IO5 | 9, 10 | strapping functions must be reviewed before use |
| `BOOT_MODE_H` | IO8 | **22** | R22 = 10 kΩ to +3V0; joint download requires IO8 high and IO9 low |
| **NC** | IO15 | 20 | JTAG-select strapping pin — deliberately unconnected |
| `+3V0` | 3V3 | 3 | |
| `EN` | EN | 8 | see §2.2 |
| `GND` | GND | 1, 2, 11, 14, 36–53 | all tied, all via-stitched |

**Deliberate choices to note in review:**
- USB D+/D− *are* connected (the vision document left this optional). The native
  USB Serial/JTAG on the C6 removes any need for a UART bridge IC, makes
  bring-up and debugging vastly easier, and costs two traces plus one ESD array.
  Production programming still uses the pogo fixture.
- IO8 is intentionally strapped high by R22 for deterministic download with
  TP7 low. IO15 remains NC. These strapping pins are not runtime spares.

### 2.2 Support circuitry

| Ref | Value | Purpose / source |
|---|---|---|
| C1 | 10 µF / 16 V X5R 0805, GRM21BR61C106KE15L ±10% | nominal entrance bulk per [Espressif C6 schematic checklist §Power Supply](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/schematic-checklist.html#power-supply); total rail capacitance maximum reviewed in docs/63; measured TX/startup rail qualification remains open |
| C2 | 100 nF / 16 V X7R 0402 | HF decoupling, at pin 3 |
| C3 | 1 µF / 16 V X5R 0402 | mid-frequency decoupling |
| R1 | 10 kΩ 0402 | EN pull-up to +3V0 |
| C4 | 1 µF 0402 | EN RC delay (≈10 ms with R1) — "do not leave EN floating" (datasheet Table 3-1) |
| SW1 | EVQPUJ02K, 4.7 × 3.5 mm body plus 1.0 mm side knob | `BTN_PROV` / IO1 → GND, R19 = 100 kΩ pull-up to +3V0 |
| R19 | 100 kΩ 1 % 0402 | external button pull-up; with C5, RC = 10 ms (engineering debounce choice, qualification pending) |
| C5 | 100 nF 0402 | SW1 debounce |
| R22 | 10 kΩ 1 % 0402 | IO8 strap pull-up; engineering resistor choice; joint-download truth table from module datasheet v1.5 Tables 4-1/4-3 |
| D1 | LED 0603, green | status |
| R2 | 3.3 kΩ 0402 | LED series — ~0.5 mA at 3.0 V; the LED is a diagnostic, not a lamp |

The [ESP32-C6-MINI-1 datasheet v1.5](https://www.espressif.com/sites/default/files/documentation/esp32-c6-mini-1_datasheet_en.pdf)
Tables 4-1/4-3 require GPIO8=1 and GPIO9=0 for joint USB/UART download.
GPIO8 defaults floating, so TP7 low alone was insufficient. R22 gives it a
defined high. Fixture holds TP7 low before releasing EN and through at least
**3 ms** after release (Table 4-2 strap hold time); independently verify strap
voltages/timing on the first boards. GPIO9 high retains normal SPI boot.
The SW1 dimensions/side operation come from [Panasonic EVQPUJ02K p.2](https://industrial.panasonic.com/cdbs/www-data/pdf/ATK0000/ATK0000COS4319.pdf).

Active-low current path: `+3V0 → R2.1 → R2.2 → D1.1 (A) → D1.2 (K)
→ U1.25 (LED_N)`. Pin names use the dedicated manufacturer-numbered KP1608SGC symbol and
Kingbright_KP1608SGC footprint: pin 1 anode, pin 2 cathode, per Kingbright
[DSAB0301 V.21B](https://www.kingbrightusa.com/images/catalog/SPEC/KP-1608SGC.pdf)
pp.1/4. The package lands are 0.8 mm squares at ±0.825 mm; use the matching
CPL orientation rather than the former generic KiCad 1K/2A convention.
`make test` guards this path and charger timer wiring for both variants.

---

## 3. U2 — SHT45-AD1F (environmental sensor)

DFN-4, 1.5 × 1.5 mm, no central pad. The selected filtered AD1F package
is 0.63 ±0.10 mm high (**0.73 mm maximum**), not the bare sensor’s
0.50 mm height ([Sensirion SHT4x v7.3, Fig. 16](https://sensirion.com/resource/datasheet/sht4x)).
I²C address **0x44**.

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
fixed electrical values. The generator reserves all four outward horizontal U2 pad exits before routing
longer paths and blocks the exact shared package-body polygon plus half trace
width. A routes its supply first, then SDA/SCL, then ground and the C6 taps;
this prevents ground wrapping around the left sensor-pad escape after local
power placement changes. B routes outer-left
SCL before inner-left SDA, then inner-right GND and outer-right supply. Both
main-board plane-access search seeds lie to the right of the neck centre; these
are geometry assumptions, not fixed electrical values. B rotates the nonpolar
C6 by 180° to place its GND tap on the inner side and supply tap on the outer
side. A retains C6 at 90°. B guides GND through a point 0.5 mm right of the
neck centre and 1.0 mm below its island end, while supply passes 1.1 mm right
and 0.3 mm below that end. These provisional routing waypoints reserve inner
and outer lanes before entering the neck; no additional conductor or via
crosses the neck. Masks use the larger interacting net-class clearance,
including 0.20 mm for ground/supply versus sensor copper. This deliberately
differs in geometry only; both
variants retain the same circuit, netlist, values and firmware. The short
horizontal exit extends to 1.3 mm from the sensor centre, a provisional routing
seed outside the package, not a measured thermal dimension.

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

### 3.2 Main-board power widths and bounded pad escapes

The provisional router uses 0.15 mm for low-current signal tracks, an engineering
geometry choice above the existing 0.127 mm fabrication minimum. Net-class
clearances still apply. The switch node uses a 0.60 mm top-layer trunk and one
bounded 0.15 mm pin-7 escape; every switch segment stays on F.Cu and no switch
via is allowed. The USB
pair is left explicitly unrouted until dedicated coupled geometry is reviewed.

Main-board Power-class trunks are at least **0.4 mm** wide. General fabrication
minimum rules precede the specific power rule: KiCad resolves matching width
rules in reverse order, so the former later 0.127 mm default could override the
power minimum. Executable KiCad controls must reject a 0.2 mm Power track away
from any approved escape and accept a 0.4 mm trunk.

Only explicitly generated **fully enclosed** `Power escape *` corridors permit
0.15 mm pad/plane neckdowns, with a maximum 2.5 mm routed path per neckdown.
The corridor is emitted from tagged, reviewed generator tracks; it is not a
blanket exception for an IC, net or board region. The sensor's four 0.15 mm
feeders retain their separate thermal allowance and forbidden-via rules.
Negative controls reject a thin track extending outside its corridor.

The Switch class also enforces its 0.6 mm trunk width. The checkpoint router
leaves the USB differential pair unrouted until a coupled path passes its actual
KiCad constraints. Failed maze branches are removed back to their last anchored
junction; cleanup retains complete paths and fixed sensor-island routing. These
rules improve layout validation, but remaining airwires still block fabrication.

For a screening calculation, assume copper resistivity **1.8 ×10⁻⁸ Ω·m**
(an explicit engineering assumption, not a laminate or temperature measurement),
35 µm outer copper from the shared stackup, length 2.5 mm and width 0.15 mm:
`R = ρL/(wt) = 8.6 mΩ`. At requirement E-07's 500 mA capability, this gives
4.3 mV DC drop and 2.1 mW loss **per neckdown**. Sum series neckdowns for the
actual supply path. These figures do not qualify temperature rise, fabrication
thickness tolerance, current transients, via losses or regulator-loop inductance;
those remain layout review and rail/thermal bench gates before unrestricted use.


### 3.3 Reviewed local power loops and ground access, 2026-10-21

The shared placement reserves C1/C7/C8/C9/C10/C11 and Q1 before small-signal
packing. U3 rotates 270° and L1 180°, without changing their centres or the
netlist: pin 7 now faces L1; the VOS pin 8 runs directly to C8's output pad on
F.Cu rather than depending on a distant plane connection. C7 returns locally
to the regulator ground region; C8 and charger bypass capacitors have local
return vias. U4 OUT/BAT bypass capacitors no longer land near the remote body
end. Full power routing and physical startup/load-step review remain open.

The 0.5 mm U3 pad pitch and 0.25 mm Switch clearance prevent a 0.6 mm
trace escaping pin 7 between its neighboring pads. One explicitly tagged
`switch-neckdown` may be 0.15 mm wide, must start on U3.7 and end on its 0.6 mm
trunk, and has a **1.2 mm maximum path**; the reviewed route is **1.15 mm**.
These are engineering geometry choices, not TI recommended dimensions.
Additional/chained narrow tracks, displaced escapes, other layers and Switch
vias fail generator validation; actual KiCad controls enforce the fully
contained `Switch escape *` area and reject thin tracks partly outside it.
The 0.6 mm trunk, 0.25 mm clearance and four-layer stackup remain unchanged.

Using the stated resistivity assumption of 1.8×10⁻⁸ Ω·m and 35 µm copper,
a worst-permitted 1.2×0.15 mm escape has R=4.11 mΩ. At the TPS62840's
750 mA output capability this screens as 3.09 mV /2.31 mW DC; the output
rating is not the peak switch current. Ripple/peak current, parasitic
inductance, copper tolerance and switching stability still require review and
measurement against [TI TPS62840 §§7.5,9.2,10](https://www.ti.com/lit/ds/symlink/tps62840.pdf).

U1 has four ground vias between the nine centre-land tiles, derived from the
vendored primary land-pattern geometry; their drill holes avoid the paste
lands. U4 has four 0.6/0.3 mm GND vias at local (±0.55,±0.55), plus a direct
VSS8-to-EP link per [SLUS810N §12.3](https://www.ti.com/lit/ds/symlink/bq24074.pdf).
TI RGT0016B drawing 4219033/A08/2016 supplies those via centres and a 0.2 mm
example bore; use of the project's 0.3 mm bore is an explicit engineering
choice. Under-EP vias require accepted filled/capped/planarized processing
and reflow/paste review before ordering; generic front/back tent flags do not
prove a seal inside the exposed-pad mask opening. See docs/63 and EDS-17.

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
| C8 | 10 µF / 16 V X5R 0805 (output), GRM21BR61C106KE15L | datasheet §9.2.2.2; effective capacitance/stability remains qualification, see docs 63 |
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
| 1 | TS | `PACK_TS`: J2.2 → selected pack's **103AT-2 NTC** → J2.1/GND; no direct MCU connection; R21 DNP (see §5.2) |
| 2, 3 | BAT | `VBAT` |
| 4 | /CE | `CHARGE_EN_N`: R18 = 47 kΩ to `VBUS`, Q1 drain; VBUS disables charging before MCU power-up |
| 5 | EN2 | `USB_EN2` (IO14) + R20 = 100 kΩ to +3V0; high with EN1 high selects standby |
| 6 | EN1 | `USB_ISEL` (IO21) + R8 = 100 kΩ to +3V0 |
| 7 | /PGOOD | `PG_N` (open drain) + R9 = 100 kΩ pull-up to `+3V0` |
| 8, 17(EP) | VSS | `GND` |
| 9 | /CHG | `CHG_N` (open drain) + R10 = 100 kΩ pull-up to `+3V0` |
| 10, 11 | OUT | `VSYS` |
| 12 | ILIM | R11 (see below) |
| 13 | IN | `VBUS` |
| 14 | TMR | **NC** — default safety timers enabled; grounding this pin disables them (TI SLUS810N, Pin Functions) |
| 15 | ITERM | R12 (see below) |
| 16 | ISET | R13 (see below) |

EN1 and EN2 are both pulled high to the valid MCU rail. The bring-up image
keeps both high: TI Table 7-2 standby, not USB500. Neither pull-up establishes
a safe logic high before the MCU rail exists; startup and loss-of-rail remain
qualification cases. See [ADR-001](adr/001-controlled-prototype-power-and-wake.md).

### 5.1 Charge current — the most thermally consequential resistor on the board

Datasheet K-factors: K<sub>ISET</sub> = 890 AΩ, K<sub>ILIM</sub> = 1550 AΩ,
K<sub>ITERM</sub> = 0.0300 (ISET mode).

| Ref | Function | Equation | Value | Result |
|---|---|---|---|---|
| R13 | fast charge | nominal 890/4420; worst case 975/(4420 × 0.99) | **4.42 kΩ 1 %** | 201 mA nominal, **≤223 mA** worst case |
| R11 | ILIM fallback | nominal 1550/8060; worst case 1720/(8060 × 0.99) | **8.06 kΩ 1 %** | **192 mA nominal, ≤216 mA** if EN2=1/EN1=0; prohibited by bring-up policy |
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

J2.2 connects the pack 103AT-2 NTC directly to the BQ24074 TS pin.
**R21 is mandatory DNP:** it separates raw `PACK_TS` from MCU
`PACK_TS_SENSE` / IO3. The earlier direct ADC connection had no proven safe
voltage under an open NTC or an unpowered MCU. TI SLUS810N §9.3.6 does not
provide a design guarantee limiting open TS to a powered-down MCU's input range.
A nominal room-temperature voltage does not establish fault safety.
Do not populate R21 as a plain zero-ohm link. EDS-15 requires a protected sensing
interface and loading/error analysis before firmware charge supervision.

R18 = 47 kΩ pulls `/CE` to VBUS; Q1 isolates IO18 from VBUS and R7 = 100 kΩ
holds Q1 off at reset. These are unchanged. At the charger's 4.35 V minimum
operating input, using TI's approximate 285 kΩ internal CE pull-down,
4.35 × 285/(285 + 47) = **3.73 V**, above its 1.4 V high threshold.
At nominal 5 V, R18 requires approximately **106 µA** sink current.
This nominal calculation is not startup qualification; slow-ramp behavior and
MCU rail loss remain EDS-9Q tests. The bring-up firmware never asserts Q1.

The charger direct-NTC window is approximately 0–50 °C, whereas pack drawing
FD_3245_20 limits charging to 0–45 °C. Therefore native TS alone cannot qualify
charging. Supplier confirmation, a protected measured temperature interface,
reviewed guard bands, fault/timer tests and bounded fail-safe shutdown are all
required before charging is authorized. A supervised lab image must have its
own reviewed procedure; the shipped engineering image keeps charging disabled.

| Ref | Value | Purpose |
|---|---|---|
| C9 | 10 µF / 16 V X5R 0805 | IN bypass (datasheet: 1–10 µF) |
| C10 | 10 µF / 16 V X5R 0805 | OUT bypass |
| C11 | 10 µF / 16 V X5R 0805 | BAT bypass |
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
| U5 | USBLC6-2SC6, dedicated ST_USBLC6_SOT23_6 footprint | ESD on D+/D− and VBUS; 1.2 × 0.6 mm lands at x ±1.15 mm, y pitch 0.95 mm, ST DS4260 Rev 7 Fig.19 |
| C14 | 100 nF 0402 | VBUS local |
| — | shield → `GND` | direct tie for Rev 1; document if EMC testing later wants an RC |

`USB_D_P`/`USB_D_N` use KiCad-recognized complementary P/N suffixes; the
former DP/DM suffixes did not establish a pair for differential rule checks.
The provisional pair geometry is 0.25 mm width with a 0.20 mm preferred gap,
bounded to 0.15–0.25 mm as an explicit engineering routing assumption.
The maximum is necessary: [KiCad 10 custom-rule documentation](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom-design-rules)
defines uncoupled tracks by nonparallel geometry or spacing outside the allowed
gap range. A minimum/optimum without a maximum accepted widely separated
parallel tracks. Isolated controls now reject a 6 mm pair at 2 mm centre spacing
and accept 0.25 mm tracks at 0.20 mm gap. These dimensions do not establish
90 Ω impedance; the exact stackup/field calculation and assembler review remain
open before layout approval.
D+/D− route to IO13/IO12 as a differential pair, 90 Ω target, kept short and
away from the antenna and the inductor.

### 7.1 Source-current policy — prototype standby, controlled bench only

The shared initial prototype implements the disposition in
[ADR-001](adr/001-controlled-prototype-power-and-wake.md): EN1/EN2 default high
while +3V0 is valid, and the bring-up image drives both high (standby). It never
selects USB500, USB100 or resistor-programmed ILIM. USB is for battery-powered
serial/debug only in this image. Battery-less startup is unsupported; the
factory uses a declared battery simulator/fixture supply at VBAT.

A separate reviewed lab image may select EN1=EN2=0 (USB100) only under a
supervised, measured bench-source protocol. An ordinary data host, open serial
port, SOF traffic, Type-C Rd, PG_N or adapter appearance does not authorize a
higher current mode. C6 USB Serial/JTAG is fixed-function hardware; the pinned
[ESP-IDF v5.5.4 API](https://github.com/espressif/esp-idf/blob/v5.5.4/components/esp_driver_usb_serial_jtag/include/driver/usb_serial_jtag.h)
does not expose the configuration/current-allocation callback previously assumed.

R8/R20 = 100 kΩ are engineering pull-up choices. TI SLUS810N §8.5 lists
1.4 V high threshold and 10 µA high-input current; the module v1.5 Table 6-3
lists 50 nA high-input current. Treating both as adverse load, at a valid
3.0 V rail and 101 kΩ maximum resistor: 3.0 − 101000 × (10e-6 + 50e-9)
= **1.98 V**, above 1.4 V. This is a static margin calculation, not proof
under reset pulls, transient coupling or rail loss; those must be measured. Before
the rail exists, those pull-ups are not high; USB100 startup or supply cycling
can occur. Capture EN1, EN2, +3V0, VSYS, VBUS and total input current during
attach, reset, suspend, detach, sleep, brownout and no-pack cases. Standby selection
alone is not proof of complete USB suspend compliance. EDS-10Q/11/12/13 remain
open for unrestricted operation; E-03 charging is not yet fulfilled.


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
with 51021-0300. The board silk prints the explicit cavity legend `J2 1- 2T 3+`;
J2's 90° placement makes the actual pad row vertical, so the legend must not
imply a horizontal viewing order. Its footprint is verified against
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
| 7 | `BOOT_N` (IO9) | force download mode independently of SW1 |
| 8 | `UART_TX` | console |
| 9 | `UART_RX` | console |
| 10 | `USB_D_P` | native USB flashing via fixture |
| 11 | `USB_D_N` | native USB flashing via fixture |
| 12 | `SDA` | I²C bring-up / sensor probe |
| 13 | `SCL` | I²C bring-up / sensor probe |
| 14 | `CHG_N` | charger state |
| 15 | `PG_N` | USB-present state |
| 16 | `TEST_MODE` (IO20) | fixture pulls low → factory test firmware |

---

### Main-board sensor routing clarification (2026-09-18)

The no-via requirement applies spatially to the sensor island/neck on B and the
sensor quiet area on A. SDA/SCL may change layers on the main board to reach
bottom-side TP12/TP13. The former global net-class via ban made those test pads
unroutable. Both generators now allow those main-board branches at 0.15 mm while
retaining the existing island routes and spatial via prohibition. KiCad negative
controls exercise an illegal neck via and a legal main-board sensor via.

### Locked prototype architecture disposition (2026-10-12)

| Decision | Locked implementation | Evidence still required |
|---|---|---|
| EDS-14 architecture | SW1 on IO1 with R19; independent IO9 TP7 download strap | button wake, held-button and boot tests; provisioning remains unimplemented |
| EDS-13 prototype | MCU-controlled EN2 and both EN pins pulled to valid +3V0; bring-up standby only | startup/loss-of-rail and measured suspend current; unrestricted source policy |
| EDS-15 prototype | R21 mandatory DNP isolates ADC from raw charger TS | protected temperature sensing redesign and qualification before charging |

Both A and B use these same schematic/netlist/firmware decisions. This locks a
controlled prototype disposition, not product qualification or compliance.

Variant B electronics body now uses the same 30 mm width as A, adding 2 mm
right-side passive clearance while retaining shared electronics anchors. Neck
width/length and the shared electrical platform remain as specified.

## 10. Open items (this document does **not** close them)

| # | Item | Owner | Closing gate |
|---|---|---|---|
| EDS-1 | Exact USB-C receptacle MPN (JLCPCB basic-part availability drives this) | hardware maintainer | before prototype order |
| EDS-4 | Whether the bounded 223 mA charging design is thermally acceptable in the enclosure, or the 100 mA option is required | hardware/test maintainer | thermal Test 3 |
| EDS-5 | 3.0 V vs 3.3 V — R6 value for the series build | hardware maintainer | prototype power + RF measurement |
| EDS-6 | Whether precision sleep timing is needed; IO1 wake assignment requires an ADR before adding a crystal | firmware maintainer | deep-sleep timing drift measurement |
| EDS-7 | Antenna: flush with board edge (Rev 1) vs overhanging the outline | hardware maintainer | RF test in the finished enclosure |
| EDS-8 | Neck width 3.0 / 3.5 / 5.0 mm for Variant B | hardware/mechanical maintainer | first bare-PCB mechanical inspection + Test 1 |
| EDS-9Q | Qualify LP702040 supplier drawing, pack NTC thresholds, protection, timer/fault behavior and assembled retention | hardware maintainer | before enclosed battery charging |
| EDS-10Q | Measure prototype standby/startup and qualify the eventual USB source policy | hardware/firmware maintainer | before unrestricted USB use |
| EDS-11 | Prove C6 USB configuration/current-allocation observability, descriptor power request and suspend handling; USB500 remains disabled | firmware/hardware maintainer | supported source-policy/descriptor review before unrestricted USB or USB500 implementation |
| EDS-13 | Qualify EN1/EN2 rail pull-ups and standby; complete unrestricted source policy | hardware/firmware maintainer | ADR-001 schematic review for controlled prototype; rail-rise/loss and suspend measurements before unrestricted USB |
| EDS-14 | Validate locked IO1 runtime wake and independent IO9 download strap | hardware/firmware maintainer | ADR-001 pin review, then button/wake/held-button bench test |
| EDS-15 | Protected PACK_TS sensing, open-NTC and unpowered-MCU fault bounds; R21 remains DNP | hardware/firmware maintainer | protected interface ADR before charge-enabled build, then bench qualification |
| EDS-12 | Prove the maximum CE/USB_ISEL deassertion latency on a hung CPU and before sleep; a pull-down cannot override an actively driven GPIO | firmware/hardware maintainer | watchdog/reset design review, then fault-injection qualification before charging |
| EDS-16 | Bound effective C7 input and total +3V0 capacitance C1/C2/C3/C6/C8 including zero-bias startup, tolerance, temperature and aging; 21.2 µF nominal /26.818 µF positive-tolerance/temperature upper envelope; C8 minimum uses stated typical bias assumptions, not a guaranteed3–40 µF effective envelope | hardware maintainer | before controlled prototype order: desk review of stated component bounds/derating assumptions; before unrestricted operation: accepted part-specific effective bounds and measured startup/TX/load-step stability (docs/63) |
| EDS-17 | Qualify U4 under-EP via fill/cap/planarity, stencil/paste and hidden-joint inspection; repriced manufacturer acceptance | hardware maintainer and assembler | before controlled prototype order; source/drawing/CPL review and accepted filled/capped/planarized fabrication + paste/reflow process |


## 11. Review checklist for this spec

- [ ] every ESP32 module pin number re-checked against datasheet v1.5 Table 3-1
- [ ] SHT4x pin 1 orientation re-checked against the Sensirion land pattern
- [ ] BQ24074 EP tied to GND with a via array
- [ ] no unreviewed strapping-pin load (IO8 R22 high and IO9 TP7 download are intentional; IO15, IO4, IO5 unused)
- [ ] every open-drain charger output has exactly one pull-up
- [ ] CC1 and CC2 have separate 5.1 kΩ resistors
- [ ] battery connector polarity printed on silkscreen
- [ ] all four island nets, and only those four, cross the neck at 0.15 mm
