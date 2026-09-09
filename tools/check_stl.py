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
import math
import struct
from pathlib import Path

from .boardgen.enclosure import FLOOR, LID, build
from .boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[1]
TOL = 0.05


def bbox(path: Path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0
    if count and len(data) == 84 + 50 * count:
        v = [struct.unpack_from("<3f", data, 84 + 50 * i + 12 + 12 * j)
             for i in range(count) for j in range(3)]
    else:
        try:
            t = data.decode("ascii")
        except UnicodeDecodeError:
            return None
        v = [tuple(map(float, m.groups())) for m in
             re.finditer(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", t)]
    if any(not math.isfinite(n) for p in v for n in p):
        return None
    if not v:
        return None
    xs, ys, zs = zip(*v)
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def main() -> int:
    bad = 0
    checked = 0
    for k, v in VARIANTS.items():
        c = build(v)
        # The lid's 1.2 mm locating lip is always present. Hold-down pillars
        # extend farther only when the placement search found a legal one.
        lid_reach = max(1.2, c.top_clear if c.holddowns else 0.0)
        want = {
            "base": (c.outer_w, c.outer_h, FLOOR + c.inner_z),
            "lid": (c.outer_w, c.outer_h, LID + lid_reach),
        }
        for part, w in want.items():
            f = ROOT / "mechanical" / f"case-{k}-{part}.stl"
            if not f.exists():
                print(f"    {f.name} not rendered (openscad not run)")
                bad += 1
                continue
            try:
                got = bbox(f)
            except (OSError, ValueError, struct.error):
                got = None
            checked += 1
            if got is None:
                print(f"    {f.name} is empty")
                bad += 1
                continue
            # Pillars end at the PCB top when the lid seating face is closed.
            axes = (0, 1, 2)
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
