# 40 — Floorplans A and B

Both boards are emitted from one model (`tools/boardgen/`). The parts, values,
netlist, net classes and design rules are identical; `variants.py` is the only
file that differs between them, and it contains outline, sensor position and
thermal zones — nothing electrical.

| | ![Variant A](img/floorplan-a.svg) | ![Variant B](img/floorplan-b.svg) |
|---|---|---|
| | **A — Compact**, HW A1 | **B — Thermally isolated**, HW B1 |

KiCad renders of the same two files: `img/render-a.png`, `img/render-b.png`.

## Side by side

| | **A — Compact** | **B — Thermally isolated** |
|---|---|---|
| PCB | 30 × 34 mm (1020 mm²) | 28 × 51 mm (1310 mm² incl. island) |
| Layers | 4, FR-4, 1.6 mm | identical |
| Parts | 41 placements | identical |
| Sensor position | bottom edge, board centre | on a 18 × 9 mm island |
| Neck | — | 3.5 × 8.0 mm FR-4, 4 × 0.15 mm traces |
| Nearest heat source to the sensor | **11.3 mm** (D1) | **23.1 mm** (J1) |
| Conduction, electronics → sensor | **70 mW/K** | **1.2 mW/K** |
| Isolation | — | **57× better** |
| Assembly difficulty | identical (single-sided SMT, same stencil apertures) | identical |
| Panel area / PCB cost | lower | ~28 % more area |
| Mechanical risk | none | the neck: 3.5 mm of FR-4 carrying an island |
| Enclosure | one chamber, vents at the sensor edge | two chambers with a dividing wall at the neck |

## What the layout actually decided

**The connectors moved to the side edges.** In B the bottom edge is where the
thermal neck leaves the board, and both variants share one placement table — so
the USB-C receptacle sits on the left edge and the JST on the right in *both*.
This is a good example of the shared-model discipline paying off: a decision
forced by B automatically applies to A, and the two boards stay comparable.

**The antenna keep-out costs 170 mm².** Espressif ask for ~15 mm clear around
the module antenna. Neither board is 30 mm wider than the module, so in-plane we
give the antenna the **full width of the board for its whole length** and buy the
rest of the clearance from the enclosure. That is ~17 % of variant A's area
spent on a strip with no copper on any layer. It is also the only place on the
board with room for a silkscreen title block, which is where it now lives.

**There are no mounting holes.** M-04 forbids metal fasteners near the antenna;
a nylon M2 boss costs ~19 mm² on a board this size; and the printed enclosure can
register the board on ribs against the USB-C and JST cut-outs. Revisit at Rev 2
if that retention proves unreliable.

**Reference designators are not on the silkscreen.** Forty 0402s on 30 × 34 mm
cannot be silk-labelled legibly — KiCad's silk DRC said so, 93 times. The
assembly drawing (`F.Fab`/`B.Fab`, exported to `hardware/outputs/*/assembly/`)
carries every reference. The silkscreen carries what a human needs while holding
the board: name, revision, battery polarity, USB and pogo labels.

## Why A cannot be fixed by moving the sensor

See `45-thermal-model.md` for the derivation. The short version:

> On a 4-layer board the copper planes conduct **112×** more heat than the FR-4.
> The board is an isothermal slab. Moving the sensor from 11 mm to 23 mm on the
> *same* copper changes the conduction path by about a factor of two — against a
> convection path that is 20–60× weaker. Variant A's sensor reads the printed
> circuit board, not the room, under every plausible enclosure assumption.

That is the case for B, and it is also the case against spending more effort on
A's placement. A is not a bad layout; it is a good layout of a geometry that
cannot win. Its value is as the **control** in the experiment.

## Why B is not obviously right either

1. **The neck is 3.5 mm of FR-4 holding an island.** Bare-board handling, depanel
   and assembly all apply force there. First bare-PCB inspection has to check it
   (open item EDS-8: 3.0 / 3.5 / 5.0 mm).
2. **B's coupling depends on the enclosure**, A's does not. B without a proper
   two-chamber case and vents at the island is worth much less than the 57×
   suggests. That moves risk from the PCB, where we control it, to the printed
   part, where we control it less.
3. **28 % more board area, a longer enclosure, and a shape that is harder to
   panelise.** Real money at 20 units, and more at 200.
4. The four island traces are the entire electrical path to the sensor and they
   are 0.15 mm wide with no redundancy. An I²C bus that flakes there is a scrap
   board, not a rework.

## Routing status — stated plainly

Both boards are **placement-complete and rule-complete, not routed**. What is in
the files: outline, all 41 placements, 4-layer stackup, all 29 nets, GND pour on
F/In1/B, +3V0 plane on In2, RF and thermal keep-outs, GND stitching, silkscreen,
and the four sensor-island nets routed at 0.15 mm with their plane vias.
80 ratsnest connections per board remain.

Those four nets are routed here rather than left to the layout session because
they carry a *rule* — 0.15 mm, no vias, nothing else near them — and the same
rule is written into each variant's `.kicad_dru`, so KiCad's DRC enforces it
against whoever routes the rest. `hardware/drc-budget.json` records the 80 and
may only ever decrease.

KiCad DRC on both variants: **0 errors**, 5 and 4 warnings, all three warning
types reviewed and justified in `tools/drc_gate.py`.

## Prior expectation, to be falsified

75 % on B. The number is a prior, not a result. `50-thermal-ab-test-plan.md`
is how we find out, and it is designed to be able to say "A is good enough" —
which, for a room-comfort sensor that spends 99.9 % of its life asleep and cold,
is a real possible answer.
