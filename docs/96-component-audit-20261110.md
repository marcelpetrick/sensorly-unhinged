# 96 — Component audit, 2026-11-10

Desk audit of the shared electrical platform for both A and B. This records what
the committed sources prove; it does not approve purchasing, placement or
charging. The canonical component list and netlist are
[`tools/boardgen/design.py`](../tools/boardgen/design.py), the generated
purchase view is [`hardware/outputs/bom.csv`](../hardware/outputs/bom.csv), and
manufacturer drawing comparisons already made are in
[`docs/63-assembly-qualification.md`](63-assembly-qualification.md). Source
links below are manufacturer documents or product pages unless stated otherwise.

## Method and result

- Parsed the committed BOM and imported the common model without regenerating
  files. All **47** BOM references and every BOM field match the model one for
  one, including R21 marked `Populate=no`. Every row has an exact MPN,
  manufacturer and nonempty second-source/risk field. All project footprints
  exist and every wired pad number is present. This is a consistency check,
  not a manufacturer pad or orientation proof.
- Read the high-consequence pin/pad and value records in the existing rendered
  manufacturer-drawing review, §Pin and footprint record of
  [63](63-assembly-qualification.md#pin-and-footprint-record), and checked
  selected manufacturer datasheet text online. No confirmed **new**
  model-versus-datasheet pin, value or land-pattern defect was found in this
  desk pass. I did not independently render or dimensionally compare every
  primary drawing, or inspect a physical first article. The earlier review is
  the source of dimensional evidence used below.
- Every BOM line's `Second source` entry is either an **unqualified candidate**
  or an explicit single-source risk. None is an approved substitute. This is
  consistent with [63](63-assembly-qualification.md), but the repository's
  “second sources or accepted risk” rule is fulfilled only for design
  exploration, not the 20-unit release.

From the repository root, this read-only check reproduces the model/BOM and
footprint/pad findings (Python 3 with the project's dependencies installed):

```sh
python3 - <<'PY'
import csv
from pathlib import Path
from tools.bom import bom_rows
from tools.boardgen.design import NETS, PARTS
from tools.boardgen.geometry import get

rows = list(csv.DictReader(Path('hardware/outputs/bom.csv').open(newline='')))
expected = [{key: str(value) for key, value in row.items()} for row in bom_rows()]
assert rows == expected, 'committed BOM differs from shared model'
refs = {ref for row in rows for ref in row['Refs'].split(',')}
assert len(refs) == 47
assert refs == {part.ref for part in PARTS if not part.exclude_from_bom}
assert {part.ref for part in PARTS if part.exclude_from_bom} == {
    f'TP{n}' for n in range(1, 18)
}
for part in PARTS:
    name = part.footprint.split(':', 1)[1]
    assert Path('hardware/lib/sensorly.pretty', name + '.kicad_mod').is_file(), part.ref
    pads = set(get(part.footprint).pads)
    wired = {pad for pins in NETS.values() for ref, pad in pins if ref == part.ref}
    assert wired <= pads, (part.ref, wired - pads)
print('PASS: 47 BOM references; 17 fixture pads; model, footprints and wired pads consistent')
PY
```

This checks number existence, not electrical function, pad dimensions, symbol
graphics, placement rotation or physical probe access. `make erc drc` and the
full `./localPipeline.sh` remain the project gates for generated boards.

## Every BOM component group

“Matched” below means the model's MPN, nominal value, and footprint naming
agree with the cited desk record. It does **not** mean effective capacitance,
thermal behavior, solder process or supplier availability is qualified.

| References | Source and desk finding | Remaining gap |
|---|---|---|
| U1 | Espressif [ESP32-C6-MINI-1 datasheet v1.5](https://www.espressif.com/sites/default/files/documentation/esp32-c6-mini-1_mini-1u_datasheet_en.pdf) §3.2 and Fig. 11-1; pin and land comparison in [63](63-assembly-qualification.md#pin-and-footprint-record). The exact N4 module and shared nets match. | Assembler orientation; RF and rail tests. 1U is a different antenna design. |
| C1, C8, C9, C10, C11 | Exact Murata GRM21BR61C106KE15L, 10 µF/16 V X5R/0805, in [63](63-assembly-qualification.md#capacitors). C1 follows the [Espressif C6 power checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/schematic-checklist.html#power-supply); C8 nominal selection follows [TI TPS62840](https://www.ti.com/lit/ds/symlink/tps62840.pdf) §7.3/§9.2.2.2. | Part-specific effective bounds and startup/TX/charge bypass measurements, EDS-16. |
| C2, C5, C6, C12, C13, C14 | Exact Murata GRM155R71C104KA88D, 100 nF/16 V X7R/0402; manufacturer [SimSurfing base-part record](https://ds.murata.com/simsurfing/mlcc.html?oripartnumbers=%5B%22GRM155R71C104KA88J%22%5D&partnumbers=%5B%22GRM155R71C104KA88%22%5D&rgear=suaykx&rgearinfo=com) and [63](63-assembly-qualification.md#capacitors). Model's distinct decoupling/filter roles match. | Exact D reel suffix purchasing check; effective capacitance and function tests as applicable. |
| C3, C4 | Exact Murata GRM155R61C105KA12D, 1 µF/16 V X5R/0402, per [Murata SimSurfing](https://ds.murata.com/simsurfing/mlcc.html?oripartnumbers=%5B%22GRM155R61C105KA12D%22%5D&partnumbers=%5B%22GRM155R61C105KA12%22%5D&rgear=jomoqke&rgearinfo=au). C4 with R1 gives nominal 10 ms EN RC by calculation. | C3 bias bound and measured EN/reset waveform. |
| C7 | Exact Murata GRM188R61A475KE15D, 4.7 µF/10 V X5R/0603, per [Murata reference sheet](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM188R61A475KE15-01.pdf). | [TI](https://www.ti.com/lit/ds/symlink/tps62840.pdf) requires effective CIN ≥1 µF; bound at VSYS is open, EDS-16. |
| R1, R3, R4, R22 | Panasonic ERJ2RKF1002X, 10 kΩ/1%/0402; exact [manufacturer part page](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF1002X). Pull-up roles match EDS §§2–3. | Assembly/source approval; IO8 boot strap bench test, EDS-14. |
| R2 | Panasonic [ERJ2RKF3301X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF3301X), 3.3 kΩ/1%/0402. LED-current estimate is documented in EDS §2. | Low-current LED visibility test. |
| R5, R21 | Panasonic [ERJ2GE0R00X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2GE0R00X), 0 Ω/0402. R5 is fitted; **R21 is DNP** by model and BOM. | R21 must remain open until protected PACK_TS sensing is designed, EDS-15. |
| R6 | Panasonic [ERJ2RKF2673X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF2673X), 267 kΩ/1%/0402; [TI TPS62840](https://www.ti.com/lit/ds/symlink/tps62840.pdf) VSET table maps the selected baseline to 3.3 V. | Series 3.0/3.3 V decision EDS-5; VSET parasitics EDS-18. |
| R7, R8, R9, R10, R19, R20 | Panasonic [ERJ2RKF1003X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF1003X), 100 kΩ/1%/0402. Pull-down, charger status/enable and button roles match EDS §§2,5. | Standby/source-loss behavior EDS-10Q/13; hung-CPU response EDS-12; button test EDS-14. |
| R11 | Panasonic [ERJ2RKF8061X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF8061X), 8.06 kΩ/1%/0402. EDS §5 calculation using [BQ24074](https://www.ti.com/lit/ds/symlink/bq24074.pdf) KILIM gives 192 mA nominal / ≤216 mA stated tolerance case. | ILIM mode is not selected; bench/source qualification before enabling it. |
| R12 | Panasonic [ERJ2RKF3011X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF3011X), 3.01 kΩ/1%/0402. EDS §5 uses [BQ24074](https://www.ti.com/lit/ds/symlink/bq24074.pdf) ITERM rule for ≈20.4 mA nominal. | Charge termination and pack qualification EDS-9Q. |
| R13 | Panasonic [ERJ2RKF4421X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF4421X), 4.42 kΩ/1%/0402. EDS §5 uses [BQ24074](https://www.ti.com/lit/ds/symlink/bq24074.pdf) KISET limits for ≈201 mA nominal / ≤223 mA stated tolerance case. | Enclosed heat and pack current qualification EDS-4/9Q. |
| R14, R15 | Vishay CRCW04022M20FKED, 2.2 MΩ/1%/0402, per [Vishay D/CRCW e3 document 20035](https://www.vishay.com/docs/20035/dcrcwe3.pdf). EDS §6 divider math gives 0.5 ratio and 0.95 µA at 4.2 V. | ADC acquisition/calibration measurement. |
| R16, R17 | Panasonic [ERJ2RKF5101X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF5101X), separate 5.1 kΩ/1%/0402 CC resistors; EDS §7 matches sink-only design. | USB source policy and both plug orientations, EDS-11/19. |
| R18 | Panasonic [ERJ2RKF4702X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF4702X), 47 kΩ/1%/0402; EDS §5.2 /CE pull-up calculation is explicit. | Slow-rise/loss behavior EDS-9Q/13. |
| L1 | Exact Murata DFE201612E-2R2M=P2, 2.2 µH, [manufacturer product data](https://www.murata.com/products/productdetail?partno=DFE201612E-2R2M%23) and [recommended pattern p.5](https://search.murata.co.jp/Ceramy/image/img/P02/J(E)TE243A-0006.pdf). Local lands and selected model match [63](63-assembly-qualification.md#inductor). | Effective inductance under load/temperature and assembled stability; proposed DFE201210S needs relayout. |
| U2 | Sensirion [SHT4x datasheet](https://sensirion.com/resource/datasheet/sht4x) §§5–6; exact SHT45-AD1F-R2, four-pad mapping, no central pad and polyimide membrane match [63](63-assembly-qualification.md#pin-and-footprint-record). | First-article orientation and thermal A/B calibration; alternates unqualified. |
| U3 | [TI TPS62840 SLVSEC6D](https://www.ti.com/lit/ds/symlink/tps62840.pdf) pin functions and DLC drawing; eight numbered lands, no EP, match [63](63-assembly-qualification.md#pin-and-footprint-record). | C/L/VSET and powered measurements EDS-16/18. TPS62841 candidate does not support this selected baseline per [63](63-assembly-qualification.md). |
| U4 | [TI BQ24074 SLUS810N](https://www.ti.com/lit/ds/symlink/bq24074.pdf) pin functions and RGT0016B package; 16 pins plus GND EP agree with [63](63-assembly-qualification.md#pin-and-footprint-record). | Under-EP via/stencil/joint and ground-return reviews EDS-17/20; charging gates EDS-9Q/12/15. BQ24075 pin 15 differs. |
| Q1 | [onsemi 2N7002L datasheet](https://www.onsemi.com/download/data-sheet/pdf/2n7002l-d.pdf) Case 318: G/S/D pins 1/2/3 and local land pattern agree with [63](63-assembly-qualification.md#pin-and-footprint-record). | Powered /CE behavior and qualification of Nexperia candidate. |
| J1 | Exact HRO TYPE-C-31-M-12 candidate; [HRO drawing hosted by LCSC](https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf?productCode=C165948) comparison in [63](63-assembly-qualification.md#pin-and-footprint-record). A/B share 270° edge orientation. | Final MPN/supplier revision, hole fit and assembler preview EDS-1/19. GCT candidate requires relayout. |
| J2 | Molex 53261-0371; [Molex drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/532/53261/532610271_sd.pdf) comparison in [63](63-assembly-qualification.md#pin-and-footprint-record). Model maps 1 GND, 2 PACK_TS, 3 VBAT. | Pack harness cavity continuity, source drawing/revision, assembler preview EDS-9Q. |
| D1 | Kingbright [KP-1608SGC drawing](https://www.kingbright.com/attachments/file/psearch/000/00/20160808bak/KP-1608SGC%28Ver.21B%29.pdf): 1 anode / 2 cathode as adapted library and [63](63-assembly-qualification.md#pin-and-footprint-record). | Placement preview and visibility test. Generic LED substitutions need orientation review. |
| SW1 | Panasonic [EVQ-PUJ02K specification](https://industrial.panasonic.com/cdbs/www-data/pdf/ATK0000/ATK0000COS4319.pdf) side-actuated land/terminal comparison in [63](63-assembly-qualification.md#pin-and-footprint-record). | Switch placement, service access and wake/debounce test EDS-14. |
| U5 | [ST USBLC6-2 datasheet](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) Fig. 1/Fig. 19: paired IO pins 1/6 and 3/4, GND 2, VBUS 5, and dedicated six-pad land geometry match [63](63-assembly-qualification.md#pin-and-footprint-record). | Supplier/assembly approval; PRTR5V0U2X is an unqualified candidate, not an approved same-footprint replacement. |

## Outside the assembly BOM

- **TP1–TP17** are 17 `TestPad_D1.5mm_Bottom` fixture targets in the shared
  model, each `exclude_from_bom=True`. They are copper footprints, not purchased
  components or CPL placements. TP1 and TP17 both connect to GND; the other
  15 nets and purposes are in [EDS §9](30-electrical-design-spec.md#9-design-for-test-j3-pogo-field).
  The generated [A/B fixture map](41-fixture-map.md) lists their actual bottom
  copper coordinates. It warns that the physical target pattern is **not** a
  regular grid, despite the nominal grid description in EDS §9. Probe tip,
  registration, travel and clearance need fixture qualification; EDS-19 remains
  open.
- **LP702040 pack, protection circuit, 103AT-2 NTC, configured three-wire
  harness and mating 51021-0300 housing** are external to the board BOM. They
  have separate drawing and incoming-cavity inspection requirements in
  [EDS §8](30-electrical-design-spec.md#8-selected-battery-and-connector-locked-architecture) and
  [power safety qualification](51-power-safety-qualification.md). The J2 BOM
  line alone does not qualify the assembled battery interface or a second pack
  source (EDS-9Q).
- **Enclosure A/B, vents, sensor chamber, battery retention, insulation and
  fixture hardware** are also outside the electrical BOM. The parametric
  sources are [case A](../mechanical/case-a.scad) and
  [case B](../mechanical/case-b.scad); tolerances and physical checks are in
  [enclosure design](80-enclosure.md) and
  [prototype-to-production sequence](65-prototype-to-production.md).

## Disposition

No BOM or library edits are justified by a confirmed new defect in this pass.
The unresolved items above remain in the **Open** table of
[`docs/30-electrical-design-spec.md`](30-electrical-design-spec.md#10-open-items-this-document-does-not-close-them)
and in [63](63-assembly-qualification.md). Before a controlled prototype order,
the named owners must retain accepted supplier drawings and assembly previews,
resolve EDS-16/17/18/19/20 desk gates, and keep the R21/charging restrictions.
Before a release claim, `make release-check` and the physical qualification
records still apply.
