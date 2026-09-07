# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Footprint geometry: load the project library, transform courtyards, check overlaps.

This is what lets us produce two boards from one model and still be sure that
neither of them has parts sitting on top of each other or hanging off the edge -
without needing KiCad installed to tell us.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "hardware" / "lib" / "sensorly.pretty"

# The ESP32 module's F.CrtYd deliberately encodes Espressif's 15 mm antenna
# keep-out, which is larger than either of our boards. For mechanical overlap
# checking we use the module body; the keep-out is enforced separately as a
# rule zone so that the violation is reported as what it is.
BODY_OVERRIDE = {
    "ESP32-C6-MINI-1": (-6.85, 6.85, -11.15, 5.85),
}


@dataclass
class Footprint:
    name: str
    text: str
    courtyard: tuple[float, float, float, float]   # xmin, xmax, ymin, ymax (local)
    pads: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    pad_size: dict[str, tuple[float, float]] = field(default_factory=dict)
    bottom: bool = False


_num = r"([-\d.]+)"


def _blocks(text: str, head: str):
    """Yield the source of every top-level (head ...) s-expression block."""
    i = 0
    tok = "(" + head
    while True:
        i = text.find(tok, i)
        if i < 0:
            return
        j, depth = i, 0
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield text[i:j + 1]
        i = j + 1


def _bbox(text: str, layers: tuple[str, ...]):
    pts: list[tuple[float, float]] = []
    for head in ("fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc"):
        for body in _blocks(text, head):
            if not any(f'(layer "{lay}")' in body for lay in layers):
                continue
            if head == "fp_circle":
                c = re.search(rf"\(center {_num} {_num}\)", body)
                e = re.search(rf"\(end {_num} {_num}\)", body)
                if c and e:
                    cx, cy = float(c.group(1)), float(c.group(2))
                    r = math.hypot(float(e.group(1)) - cx, float(e.group(2)) - cy)
                    pts += [(cx - r, cy - r), (cx + r, cy + r)]
                continue
            pts += [(float(a), float(b)) for a, b in
                    re.findall(rf"\((?:start|end|xy|center|mid) {_num} {_num}\)", body)]
    if not pts:
        return None
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts))


def load(name: str) -> Footprint:
    short = name.split(":", 1)[-1]
    text = (LIB / f"{short}.kicad_mod").read_text()
    if short in BODY_OVERRIDE:
        cy = BODY_OVERRIDE[short]
    else:
        cy = _bbox(text, ("F.CrtYd", "B.CrtYd")) or _bbox(text, ("F.Fab", "B.Fab"))
    if cy is None:                       # e.g. mounting hole: fall back to pads
        cy = (-1.5, 1.5, -1.5, 1.5)
    pads: dict[str, list[tuple[float, float]]] = {}
    size: dict[str, tuple[float, float]] = {}
    for body in _blocks(text, "pad "):
        name = re.search(r'\(pad "([^"]*)"', body).group(1)
        at = re.search(rf"\(at {_num} {_num}", body)
        sz = re.search(rf"\(size {_num} {_num}\)", body)
        if not at:
            continue
        pads.setdefault(name, []).append((float(at.group(1)), float(at.group(2))))
        if sz:
            # Repeated numbers need not have identical shapes (USB shield
            # lugs are 1x2.1 and 1x1.6 mm). Router obstacles must conservatively
            # cover every occurrence, not inherit whichever was parsed last.
            w, h = float(sz.group(1)), float(sz.group(2))
            old_w, old_h = size.get(name, (0.0, 0.0))
            size[name] = (max(w, old_w), max(h, old_h))
    bottom = '(layer "B.Cu")' in text.split("(pad", 1)[0]
    return Footprint(short, text, cy, pads, size, bottom)


_CACHE: dict[str, Footprint] = {}


def get(name: str) -> Footprint:
    if name not in _CACHE:
        _CACHE[name] = load(name)
    return _CACHE[name]


def xform(x: float, y: float, ox: float, oy: float, rot: float) -> tuple[float, float]:
    """KiCad footprint transform: rotation is CCW on screen with Y pointing down."""
    a = math.radians(rot)
    c, s = math.cos(a), math.sin(a)
    return (ox + x * c + y * s, oy - x * s + y * c)


def placed_box(fp: Footprint, ox: float, oy: float, rot: float
               ) -> tuple[float, float, float, float]:
    x0, x1, y0, y1 = fp.courtyard
    pts = [xform(x, y, ox, oy, rot)
           for x in (x0, x1) for y in (y0, y1)]
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts))


def boxes_overlap(a, b, gap: float = 0.0) -> bool:
    return not (a[1] + gap <= b[0] or b[1] + gap <= a[0] or
                a[3] + gap <= b[2] or b[3] + gap <= a[2])


def box_inside_polys(box, polys, margin: float = 0.0) -> bool:
    """True if the box lies wholly inside at least one polygon (with margin)."""
    x0, x1, y0, y1 = box
    corners = [(x0 - margin, y0 - margin), (x1 + margin, y0 - margin),
               (x1 + margin, y1 + margin), (x0 - margin, y1 + margin),
               ((x0 + x1) / 2, (y0 + y1) / 2)]
    for poly in polys:
        if all(point_in_poly(c, poly) for c in corners):
            return True
    return False


def point_in_poly(pt, poly) -> bool:
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside
