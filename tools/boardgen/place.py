"""Placement: anchored parts by hand, passives packed automatically.

The anchored parts (module, connectors, ICs, inductor, sensor, mounting holes)
are mechanically constrained and belong to a human. Everything else is a 0402
that only needs to be *near* something and *not on top of* anything, which is a
search, so we do it as a search - identically for both variants.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import geometry as G
from .design import PART_BY_REF, TESTPADS
from .variants import (ANCHORED, B_NECK_RECT, NEAR, TESTPAD_COLS,
                       TESTPAD_ORIGIN, TESTPAD_PITCH, Variant, antenna_keepout,
                       sensor_keepout)

COURTYARD_GAP = 0.10          # mm between courtyards
EDGE_MARGIN = 0.50            # mm from the board outline


@dataclass
class Placement:
    ref: str
    x: float
    y: float
    rot: float
    footprint: str
    box: tuple[float, float, float, float]


def _fits(box, v: Variant, taken, forbidden) -> bool:
    if not G.box_inside_polys(box, v.polys, margin=EDGE_MARGIN):
        return False   # passives keep the full margin; anchored parts may not
    for other in taken:
        if G.boxes_overlap(box, other, COURTYARD_GAP):
            return False
    for zone in forbidden:
        if G.boxes_overlap(box, zone):
            return False
    return True


def _spiral(step=0.25, rings=60):
    yield (0.0, 0.0)
    for r in range(1, rings + 1):
        d = r * step
        for k in range(-r, r + 1):
            yield (k * step, -d)
            yield (k * step, d)
        for k in range(-r + 1, r):
            yield (-d, k * step)
            yield (d, k * step)


def place(v: Variant) -> list[Placement]:
    placed: list[Placement] = []
    taken: list[tuple] = []

    def add(ref, x, y, rot):
        fp = G.get(PART_BY_REF[ref].footprint)
        box = G.placed_box(fp, x, y, rot)
        placed.append(Placement(ref, x, y, rot, PART_BY_REF[ref].footprint, box))
        taken.append(box)
        return box

    ako = antenna_keepout(v)
    ako_box = (ako[0], ako[1], ako[2], ako[3])
    sko = sensor_keepout(v)
    sko_box = (sko[0], sko[1], sko[2], sko[3])

    # 1. antenna / module and the other mechanically constrained parts
    for ref, (x, y, rot) in ANCHORED.items():
        add(ref, x + v.body_dx, y, rot)

    # 2. sensor and its single allowed decoupling cap
    add("U2", *v.sensor_xy, 0)
    add("C6", *v.sensor_cap_xy, 90 if v.key == "a" else 0)

    # 3. pogo field, bottom side
    tp_origin = (TESTPAD_ORIGIN[0] + v.body_dx, TESTPAD_ORIGIN[1])
    for i, (ref, _net) in enumerate(TESTPADS):
        col, row = i % TESTPAD_COLS, i // TESTPAD_COLS
        add(ref, tp_origin[0] + col * TESTPAD_PITCH,
            tp_origin[1] + row * TESTPAD_PITCH, 0)

    # 4. passives: search outward from the anchor
    forbidden = [ako_box, sko_box]
    if v.key == 'b':
        nx0, ny0, nx1, ny1 = B_NECK_RECT
        forbidden.append((nx0 - 1.0, nx1 + 1.0, ny0 - 1.0, ny1))
    unplaced = []
    for ref, (anchor, rot) in NEAR.items():
        ap = next(p for p in placed if p.ref == anchor)
        fp = G.get(PART_BY_REF[ref].footprint)
        # start just outside the anchor's courtyard
        r0 = max(ap.box[1] - ap.box[0], ap.box[3] - ap.box[2]) / 2 + 0.6
        best = None
        for dx, dy in _spiral():
            if math.hypot(dx, dy) < r0:
                continue
            for rr in (rot, (rot + 90) % 180):
                x, y = ap.x + dx, ap.y + dy
                box = G.placed_box(fp, x, y, rr)
                if _fits(box, v, taken, forbidden):
                    best = (x, y, rr)
                    break
            if best:
                break
        if best:
            add(ref, *best)
        else:
            unplaced.append(ref)

    if unplaced:
        raise RuntimeError(f"could not auto-place: {', '.join(unplaced)}")
    return placed
