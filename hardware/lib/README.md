# hardware/lib — project footprint library

`sensorly.pretty` is the **only** footprint library this project uses. Nothing
resolves against a system KiCad install, so a checkout builds the same boards on
any machine.

## Provenance

| Source | Footprints | Licence |
|---|---|---|
| [KiCad official footprint library](https://gitlab.com/kicad/libraries/kicad-footprints) | all except the three below, including `SOT-23` | CC-BY-SA 4.0 with the KiCad library exception (unlimited use in your own designs, no attribution required on the board) |
| authored here | `TI_DLC0008B_VSON-HR-8_2x1.5mm_P0.5mm`, `TestPad_D1.5mm_Bottom`, `Molex_PicoBlade_53261-0371_1x03-1MP_P1.25mm_Horizontal` | same licence as this repository |

## Authored footprints — verification record

**`TI_DLC0008B_VSON-HR-8_2x1.5mm_P0.5mm`** (TPS62840DLC)
Built from TI SLVSEC6D, package drawing **4224310/A**, "LAND PATTERN EXAMPLE":
8 pads of 0.6 × 0.25 mm, 0.5 mm pitch, row centres 1.3 mm apart, body
1.5 × 2.0 mm, **no exposed pad** (the EP exists only on the DGR/HVSSOP variant).
Pin 1 is top-left in the datasheet's top view; the silkscreen dot marks it.
Verified 2026-08-25.

**`TestPad_D1.5mm_Bottom`**
1.5 mm round pad, `B.Cu` + `B.Mask`, no paste. Assembly is single-sided top, so
the whole pogo field lives on the bare side and the fixture is a flat plate.

**`Molex_PicoBlade_53261-0371_1x03-1MP_P1.25mm_Horizontal`**
Built from Molex product drawing **532610271-SD** and cross-checked against the
KiCad official footprint of the same name: signal pads 0.8 × 1.6 mm at 1.25 mm
pitch, centres y = -2.4 mm; two 2.1 × 3.0 mm hold-down pads at x = ±3.8 mm,
y = 0.5 mm. The manufacturer PCB-component-side view shows circuit1 right with tails
downward; the local footprint is rotated180°, so circuit1 is left with tails
upward and is marked on
silk/fabrication. The simplified local footprint deliberately omits a 3D model;
the enclosure uses Molex's 3.40 mm mated height. Verified 2026-09-09.

## Substitution on the record

The connector symbols' footprint filters are adapted to the project library
namespace, and the authored TPS62840 symbol filter names its actual footprint.
This metadata-only change enables footprint-filter parity checks; it changes
no pins, land patterns or rotations. `tools/mksymlib.py` reproduces it. The
adapted connector symbol retains the upstream library licence.

Q1 uses the adapted `Onsemi_CASE318_SOT23` footprint. Pads 1/2/3 were verified as
gate/source/drain against the Nexperia 2N7002 and onsemi 2N7002L top-view
connection diagrams on 2026-09-09; both listed orderable parts share that
pinout and land-pattern family.

`L_Murata_DFE201612E` is adapted from the KiCad DFE201610P footprint and
retains the upstream CC-BY-SA 4.0 library licence/exception. The earlier
DFE201610P substitution is withdrawn: the land patterns differ.
The corrected footprint follows [Murata J(E)TE243A-0006D-01 p.5](https://search.murata.co.jp/Ceramy/image/img/P02/J(E)TE243A-0006.pdf):
two 0.8 ×1.8 mm pads, centres x=±0.8 mm (0.8 mm gap, 2.4 mm outer span).
Both variants use this pattern and the 1.2 mm body height. The adapted footprint
omits the old part's mismatched STEP model; enclosure checks use the bounded
component envelope instead. Inspected visually
against the manufacturer's recommended pattern on 2026-10-12; L1 is nonpolar.

## Before layout — the check that matters

For every non-trivial part: symbol → pin numbers → footprint → pad dimensions →
pin 1 → rotation → 3D model, against the manufacturer's own land pattern.
A footprint error is the cheapest way to turn a perfectly fabricated batch into
scrap. See `docs/30-electrical-design-spec.md` §11.


## Current desk review

The 2026-10-12 source comparison, exact passive candidate MPNs, and remaining
assembly approvals are recorded in [purchasing qualification](../../docs/63-assembly-qualification.md#desk-review-2026-10-12).
U2's land pattern and SW1's rotated land pattern were inspected against primary
manufacturer drawings. SW1 is side-actuated and its maximum body height is
1.95 mm, not a top-actuated generic 3.5 ×2.9 mm switch. No assembler orientation
or first-article approval is implied by library provenance.


`TI_RGT0016B_VQFN16_3x3mm` adapts the upstream KiCad generic QFN footprint
and retains CC-BY-SA 4.0/the KiCad exception. Copper/paste geometry follows
[TI package drawing 4219033/A, August 2016, reproduced in CDCLVP2102](https://www.ti.com/lit/ds/symlink/cdclvp2102.pdf):
0.6 ×0.25 mm perimeter pads, row centres ±1.4 mm, 0.5 mm pitch;
1.6 mm square EP 17 to GND. The single central paste opening is 1.47 mm square
(0.065 mm reduction per edge), following the manufacturer's 84% coverage
example with 0.125 mm stencil. Pin1 is top-left; numeric pad ordering retains
the verified generic footprint's ordering. No mismatched generic STEP model is
retained. This is the RGT0016B identified for BQ24074 in SLUS810N Figure 7-2;
RGT0016C is a distinct package drawing and must not be assumed equivalent.
Both variants use this footprint. Inspected 2026-10-12; assembler process
approval and thermal-pad solder inspection remain required.


`Kingbright_KP1608SGC` and symbol `KP1608SGC` adapt the upstream KiCad
LED footprint/symbol and retain their CC-BY-SA 4.0 library licence/exception.
[Kingbright DSAB0301 V.21B pp.1/4](https://www.kingbright.com/attachments/file/psearch/000/00/20160808bak/KP-1608SGC%28Ver.21B%29.pdf)
were rendered and inspected: **manufacturer pin 1=A and pin 2=K**. The adapted
symbol preserves diode graphics but swaps the generic KiCad LED's numeric
mapping. The dedicated footprint places pin 1 left/pin 2 right, with a cathode
mark at the right, using 0.8 mm square lands separated by 0.85 mm (centres ±0.825).
The generic symbol/footprint would require an explicit supplier orientation
conversion; neither is used for D1 now. Both boards change together; CPL rotation
must still be approved by the assembler. The old generic STEP model is omitted;
the manufacturer body height is 1.1 mm maximum. `tools/mksymlib.py` reproduces the
symbol adaptation.


`Onsemi_CASE318_SOT23` adapts the vendored KiCad SOT-23 footprint and retains
its upstream CC-BY-SA 4.0 library licence/exception. [onsemi 2N7002L, Case 318
Issue AU (14 August 2024), pp.4/5](https://www.onsemi.com/download/data-sheet/pdf/2n7002l-d.pdf)
were rendered and inspected. Recommended pads 0.95 ×0.56 mm, row centres ±0.975,
lead pitch 1.90 mm are implemented in the local 90° rotated coordinate convention.
Pin1 gate/pin 2 source on the left row; pin 3 drain on the right. No unverified
STEP model is retained. Both variants use the corrected recommended pattern.

To reproduce vendoring/adaptations, use `make symbols KICAD_SYMBOLS_DIR=/path/to/reviewed/kicad-symbols` (one shell line). The source
may be KiCad's flat installed libraries or the upstream split symbol tree.
The default path is `/usr/share/kicad/symbols`; explicitly record/review the
upstream revision before accepting changes. `make gen` and the ordinary pipeline
use the committed symbol library and never re-vendor from arbitrary installed
libraries. New/changed vendor inputs retain their original licence and require
an updated provenance entry.


J1's HRO 2020-12-08 drawing has been rendered and compared: local solder tails
are −Y, socket mouth+Y. The shared placement must therefore use 270° for the left
edge port; 90° would face the mouth into the board. The manufacturer PCB-edge
datum is 5.79 mm forward of the NPTH row, which is local y=−2.6 mm; local
PCB-edge y=3.19 gives board origin x=3.19 mm at 270°. See the primary drawing links
and tolerance/process disposition in [purchasing qualification](../../docs/63-assembly-qualification.md#pin-and-footprint-record).
J2's component-side view was independently checked from Molex 532610001-SD
revision E, 2023-07-24 (family drawing replacing the old 532610271-SD citation).
The local 180° view conversion preserves manufacturer pin numbering and lands.


`ST_USBLC6_SOT23_6` adapts the vendored KiCad SOT-23-6 footprint and retains
its CC-BY-SA 4.0 library licence/exception. ST DS4260 Rev 7 Figure 19 specifies
all six pads 1.2 ×0.6 mm, row centres ±1.15 mm, pitch 0.95 mm. The graphic was
also inspected from the ST-authored Rev 5 manufacturer PDF (p.12) mirrored at
the distributor; dimensions match the current primary document. The symbol's
footprint/filter are reproduced by `make symbols`. Package pin 1/6=IO1,
2=GND,3/4=IO2,5=VBUS stays unchanged. No mismatched generic STEP is retained.
Supplier revision/process approval and assembler orientation remain separate.

KiCad 10 internal-jumper connectivity is explicit for two manufacturer-confirmed
parts. `ST_USBLC6_SOT23_6` groups pads 1/6 and 3/4 according to the continuous
IO1/IO2 metal paths in [ST DS4260 Rev 7 p.1](https://www.st.com/resource/en/datasheet/usblc6-2.pdf).
GND pad 2 and VBUS pad 5 remain distinct. `Panasonic_EVQPUJ_EVQPUA` marks
duplicate pad numbers as internally common, following the common terminal rows
in [Panasonic EVQPUJ02K p.2](https://industrial.panasonic.com/cdbs/www-data/pdf/ATK0000/ATK0000COS4319.pdf).
SW1 pins 1 and 2 are distinct while the switch is released. These metadata
changes retain the vendored library licence and model internal component metal;
they do not permit copper shorts between different nets. Connector contacts
receive no corresponding assumption without a manufacturer source.

The shared J1 edge placement puts the connector front beyond the PCB. Its
front horizontal silkscreen line is omitted and the side silkscreen ends stop
at local y=3.0 mm, inside the documented PCB-edge datum y=3.19 mm. Copper,
drills, courtyard, numbering and the complete F.Fab body drawing are retained.
This is a board-printing adaptation, not a changed manufacturer land pattern.
