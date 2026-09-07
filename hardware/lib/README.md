# hardware/lib — project footprint library

`sensorly.pretty` is the **only** footprint library this project uses. Nothing
resolves against a system KiCad install, so a checkout builds the same boards on
any machine.

## Provenance

| Source | Footprints | Licence |
|---|---|---|
| [KiCad official footprint library](https://gitlab.com/kicad/libraries/kicad-footprints) | all except the two below | CC-BY-SA 4.0 with the KiCad library exception (unlimited use in your own designs, no attribution required on the board) |
| authored here | `TI_DLC0008B_VSON-HR-8_2x1.5mm_P0.5mm`, `TestPad_D1.5mm_Bottom` | same licence as this repository |

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

## Substitution on the record

The connector symbol's footprint filter is adapted to the project library
namespace, and the authored TPS62840 symbol filter names its actual footprint.
This metadata-only change enables footprint-filter parity checks; it changes
no pins, land patterns or rotations. `tools/mksymlib.py` reproduces it. The
adapted connector symbol retains the upstream library licence.

`L_Murata_DFE201610P` is used for the **DFE201612E-2R2M** inductor. Same 2.0 ×
1.6 mm land pattern; only the body height differs (1.0 mm vs 1.2 mm), which
affects the 3D model and the enclosure clearance, not the copper. Flagged so the
mechanical model uses the taller body.

## Before layout — the check that matters

For every non-trivial part: symbol → pin numbers → footprint → pad dimensions →
pin 1 → rotation → 3D model, against the manufacturer's own land pattern.
A footprint error is the cheapest way to turn a perfectly fabricated batch into
scrap. See `docs/30-electrical-design-spec.md` §11.
