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
            # Pad sizes are expressed in the pad's own coordinate system.
            # Its local angle is independent of the footprint placement angle;
            # ignoring it underestimates the long axis of rotated module pads.
            angle = re.search(rf"\(at {_num} {_num} {_num}\)", body)
            rotation = math.radians(float(angle.group(3))) if angle else 0.0
            c, s = abs(math.cos(rotation)), abs(math.sin(rotation))
            # Repeated numbers need not have identical shapes (USB shield
            # lugs are 1x2.1 and 1x1.6 mm). Router obstacles must conservatively
            # cover every occurrence, not inherit whichever was parsed last.
            w, h = float(sz.group(1)), float(sz.group(2))
            w, h = w * c + h * s, w * s + h * c
            w, h = round(w, 9), round(h, 9)
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


def sensor_package_keepout_polygon(v):
    """Upstream SHT4x package-body polygon, with notches for the four pads.

    Shared by PCB rule-area emission and route occupancy; library README
    identifies the vendored land pattern and its no-under-package restriction.
    """
    local = [(0.75, -0.55), (0.45, -0.55), (0.45, -0.25), (0.75, -0.25),
             (0.75, 0.25), (0.45, 0.25), (0.45, 0.55), (0.75, 0.55),
             (0.75, 0.75), (-0.75, 0.75), (-0.75, 0.55), (-0.45, 0.55),
             (-0.45, 0.25), (-0.75, 0.25), (-0.75, -0.25), (-0.45, -0.25),
             (-0.45, -0.55), (-0.75, -0.55), (-0.75, -0.75), (0.75, -0.75)]
    sx, sy = v.sensor_xy
    return [(sx + x, sy + y) for x, y in local]


def distance_to_segment(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    u = max(0.0, min(1.0, ((point[0]-a[0])*dx + (point[1]-a[1])*dy) / length2)) if length2 else 0.0
    return math.hypot(point[0] - a[0] - u * dx, point[1] - a[1] - u * dy)


VIA_PASTE_RESERVE = 0.10  # mm, engineering drill-to-paste registration allowance


def paste_lands(placed):
    """Conservative board-coordinate paste envelopes, including same-net lands.

    Copper rectangles contain the current zero/negative-margin paste apertures;
    rounded corners are conservatively included. Through drills cross both sides.
    """
    lands = []
    for part in placed:
        fp = get(part.footprint)
        numbers = {block.split('"', 2)[1] for block in _blocks(fp.text, 'pad ')
                   if 'F.Paste' in block or 'B.Paste' in block}
        for number in numbers:
            width, height = fp.pad_size[number]
            if part.rot % 180:
                width, height = height, width
            for x, y in fp.pads[number]:
                x, y = xform(x, y, part.x, part.y, part.rot)
                lands.append((part.ref, number, x-width/2, x+width/2,
                              y-height/2, y+height/2))
    return lands


def validate_via_paste(placed, vias):
    """Only the reviewed U4 EP array may put a through drill under paste."""
    parts = {p.ref: p for p in placed}
    u4 = parts.get('U4')
    ep = ({xform(dx, dy, u4.x, u4.y, u4.rot)
           for dx in (-.55, .55) for dy in (-.55, .55)} if u4 else set())
    lands = paste_lands(placed)
    for via in vias:
        for ref, pad, x0, x1, y0, y1 in lands:
            clearance = math.hypot(max(x0-via.x, 0, via.x-x1),
                                   max(y0-via.y, 0, via.y-y1)) - via.drill/2
            if clearance >= VIA_PASTE_RESERVE-1e-7:
                continue
            accepted_ep = (ref == 'U4' and pad == '17' and via.net == 'GND'
                           and abs(via.size-.6) < 1e-7 and abs(via.drill-.3) < 1e-7
                           and any(math.hypot(via.x-x, via.y-y) < 1e-7 for x, y in ep))
            if not accepted_ep:
                raise ValueError(f'{via.net} via ({via.x},{via.y}) drill approaches '
                                 f'{ref}.{pad} paste land: {clearance:.3f} mm')
