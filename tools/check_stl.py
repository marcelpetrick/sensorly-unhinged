# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify the rendered STLs match the enclosure model.

openscad will happily render a valid-looking solid from geometry that has drifted
from its parameters. Comparing the bounding boxes is cheap and catches the class
of error that matters: a case that is not the size the model says it is.

    python -m tools.check_stl
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from .boardgen.enclosure import FLOOR, LID, build
from .boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[1]
TOL = 0.05


def bbox(path: Path):
    t = path.read_text()
    v = [tuple(map(float, m.groups())) for m in
         re.finditer(r"vertex\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)", t)]
    if not v:
        return None
    xs, ys, zs = zip(*v)
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def main() -> int:
    bad = 0
    checked = 0
    for k, v in VARIANTS.items():
        c = build(v)
        want = {
            "base": (c.outer_w, c.outer_h, FLOOR + c.inner_z),
            "lid": (c.outer_w, c.outer_h, LID + 1.2),
        }
        for part, w in want.items():
            f = ROOT / "mechanical" / f"case-{k}-{part}.stl"
            if not f.exists():
                print(f"    {f.name} not rendered (openscad not run)")
                continue
            got = bbox(f)
            checked += 1
            if got is None:
                print(f"    {f.name} is empty")
                bad += 1
                continue
            # the lid carries hold-down pillars, so only X and Y are exact
            axes = (0, 1) if part == "lid" else (0, 1, 2)
            for i in axes:
                if abs(got[i] - w[i]) > TOL:
                    print(f"    {f.name} axis {'XYZ'[i]}: model says "
                          f"{w[i]:.2f} mm, STL is {got[i]:.2f} mm")
                    bad += 1
    if checked:
        print(f"  {checked} rendered part(s) match the enclosure model"
              if not bad else f"  {bad} mismatch(es)")
    else:
        print("  no STLs to check")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
