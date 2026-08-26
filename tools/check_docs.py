# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that the numbers written in the documents still match the design.

Specs rot the moment someone changes a constant and forgets the prose. Every
figure below is recomputed from the model and then looked for in the document
that quotes it, so a neck width changed in variants.py fails the build until the
spec agrees with it.

    python -m tools.check_docs
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from .boardgen.design import PART_BY_REF
from .boardgen.place import place
from .boardgen.thermal import model
from .boardgen.variants import B_NECK_L, B_NECK_W, VARIANTS
from .boardgen.route import ISLAND_WIDTH
from .boardgen.check import HEAT_SOURCES

ROOT = Path(__file__).resolve().parents[1]

# TI SLUS810N: I_CHG = K_ISET / R_ISET, K_ISET = 890 A.Ohm
K_ISET = 890.0
K_ILIM = 1550.0


def _r(ref: str) -> float:
    """Resistor value in ohms, parsed from the BOM value string."""
    v = PART_BY_REF[ref].value.split()[0].lower()
    mult = 1.0
    for suffix, m in (("m", 1e6), ("k", 1e3), ("r", 1.0)):
        if suffix in v:
            v = v.replace(suffix, ".")
            mult = m
            break
    return float(v.rstrip(".")) * mult if v.strip(".") else 0.0


def checks() -> list[tuple[bool, str, str]]:
    a, b = VARIANTS["a"], VARIANTS["b"]
    placed_a = {p.ref: p for p in place(a)}
    placed_b = {p.ref: p for p in place(b)}

    def nearest(placed):
        # Same heat-source set the generator's own check uses - defining it
        # twice is how the two answers drift apart.
        s = placed["U2"]
        return min(math.hypot(placed[r].x - s.x, placed[r].y - s.y)
                   for r in HEAT_SOURCES if r in placed)

    m = model()
    i_chg = K_ISET / _r("R13")
    i_lim = K_ILIM / _r("R11")

    want = [
        ("docs/30-electrical-design-spec.md", f"{ISLAND_WIDTH:.2f} mm",
         "island trace width"),
        ("docs/30-electrical-design-spec.md", f"{B_NECK_W} mm wide",
         "neck width"),
        ("docs/30-electrical-design-spec.md", f"{i_chg * 1e3:.0f} mA",
         "fast charge current from R13"),
        ("docs/30-electrical-design-spec.md", f"{i_lim * 1e3:.0f} mA",
         "input current limit from R11"),
        ("docs/40-floorplans.md", f"{a.width:.0f} × {a.height:.0f} mm",
         "variant A outline"),
        ("docs/40-floorplans.md", f"{b.width:.0f} × {b.height:.0f} mm",
         "variant B outline"),
        ("docs/40-floorplans.md", f"{B_NECK_W} × {B_NECK_L:.1f} mm",
         "variant B neck"),
        ("docs/40-floorplans.md", f"{nearest(placed_a):.1f} mm",
         "A nearest heat source"),
        ("docs/40-floorplans.md", f"{nearest(placed_b):.1f} mm",
         "B nearest heat source"),
        ("docs/40-floorplans.md", f"{m['a_total'] * 1e3:.0f} mW/K",
         "A conduction"),
        ("docs/40-floorplans.md", f"{m['neck_total'] * 1e3:.1f} mW/K",
         "B conduction"),
        ("docs/40-floorplans.md", f"{m['ratio']:.0f}×",
         "isolation ratio"),
        ("docs/40-floorplans.md", f"{m['a_cu'] / m['a_fr4']:.0f}×",
         "A copper-to-FR4 ratio"),
        ("docs/62-fabrication-3-boards.md",
         f"{(a.width / 25.4) * (a.height / 25.4):.2f} in²", "A area at the fab"),
        ("docs/62-fabrication-3-boards.md",
         f"{(b.width / 25.4) * (b.height / 25.4):.2f} in²", "B area at the fab"),
        ("docs/62-fabrication-3-boards.md", f"{m['a_cu'] / m['a_fr4']:.0f}×",
         "copper ratio quoted in the fab doc"),
        ("docs/62-fabrication-3-boards.md", f"{B_NECK_W} mm",
         "neck width quoted in the fab doc"),
        ("README.md", f"{a.width:.0f} × {a.height:.0f} mm", "A size in README"),
        ("README.md", f"{b.width:.0f} × {b.height:.0f} mm", "B size in README"),
    ]

    out = []
    for rel, needle, what in want:
        text = (ROOT / rel).read_text()
        out.append((needle in text, f"{rel}: {what}", needle))
    return out


def main() -> int:
    results = checks()
    bad = [r for r in results if not r[0]]
    for ok, what, needle in results:
        if not ok:
            print(f"    MISSING  {what} -> expected to find {needle!r}")
    print(f"  {len(results) - len(bad)}/{len(results)} documented figures "
          f"match the model")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
