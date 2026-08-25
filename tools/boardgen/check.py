"""Rule checks we can run without KiCad installed.

This is not a substitute for `kicad-cli pcb drc`. It catches the class of
mistake that is expensive and easy to make in a generated layout - parts on top
of each other, parts off the board, copper in the antenna keep-out, heat sources
next to the sensor - and it runs in CI on every commit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import geometry as G
from .design import PART_BY_REF
from .place import COURTYARD_GAP, EDGE_MARGIN, Placement
from .variants import Variant, antenna_keepout, sensor_keepout, B_NECK_RECT

HEAT_SOURCES = {"U4", "U3", "L1", "D1", "J1", "R13", "R11"}
MIN_SENSOR_CLEARANCE = 8.0        # mm, variant A target


@dataclass
class Finding:
    severity: str
    rule: str
    message: str

    def __str__(self):
        return f"[{self.severity}] {self.rule}: {self.message}"


def check(v: Variant, placed: list[Placement]) -> list[Finding]:
    out: list[Finding] = []
    by_ref = {p.ref: p for p in placed}

    # --- courtyard overlaps -------------------------------------------------
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            if G.get(a.footprint).bottom != G.get(b.footprint).bottom:
                continue                    # opposite sides never collide
            if G.boxes_overlap(a.box, b.box, COURTYARD_GAP):
                out.append(Finding("ERROR", "courtyard-overlap",
                                   f"{a.ref} and {b.ref} overlap"))

    # --- board containment --------------------------------------------------
    # Courtyards may reach the outline (a USB receptacle is meant to be flush);
    # copper may not - pads keep the copper-to-edge clearance.
    for p in placed:
        if not G.box_inside_polys(p.box, v.polys, margin=0.0):
            out.append(Finding("ERROR", "off-board",
                               f"{p.ref} courtyard leaves the board outline"))
        fp = G.get(p.footprint)
        pads = [G.xform(x, y, p.x, p.y, p.rot)
                for pts in fp.pads.values() for (x, y) in pts]
        if pads:
            pbox = (min(q[0] for q in pads), max(q[0] for q in pads),
                    min(q[1] for q in pads), max(q[1] for q in pads))
            if not G.box_inside_polys(pbox, v.polys, margin=EDGE_MARGIN):
                out.append(Finding("ERROR", "copper-to-edge",
                                   f"{p.ref} pads are closer than "
                                   f"{EDGE_MARGIN} mm to the board edge"))

    # --- antenna keep-out ---------------------------------------------------
    ako = antenna_keepout(v)
    for p in placed:
        if p.ref == "U1":
            continue
        if G.boxes_overlap(p.box, ako):
            out.append(Finding("ERROR", "antenna-keepout",
                               f"{p.ref} is inside the module antenna keep-out"))

    # --- sensor thermal clearance ------------------------------------------
    sx, sy = by_ref["U2"].x, by_ref["U2"].y
    worst = None
    for ref in HEAT_SOURCES:
        if ref not in by_ref:
            continue
        q = by_ref[ref]
        d = math.hypot(q.x - sx, q.y - sy)
        if worst is None or d < worst[1]:
            worst = (ref, d)
        if d < MIN_SENSOR_CLEARANCE:
            out.append(Finding("ERROR", "sensor-clearance",
                               f"{ref} is {d:.1f} mm from the sensor "
                               f"(minimum {MIN_SENSOR_CLEARANCE} mm)"))
    if worst:
        out.append(Finding("INFO", "sensor-clearance",
                           f"nearest heat source is {worst[0]} at {worst[1]:.1f} mm"))

    # --- island purity (variant B) -----------------------------------------
    if v.key == "b":
        nx0, ny0, nx1, ny1 = B_NECK_RECT
        neck = (nx0, nx1, ny0, ny1)
        for p in placed:
            if G.boxes_overlap(p.box, neck):
                out.append(Finding("ERROR", "island-purity",
                                   f"{p.ref} sits on the thermal neck"))
        sko = sensor_keepout(v)
        allowed = {"U2", "C6"}
        for p in placed:
            if p.ref in allowed:
                continue
            if G.boxes_overlap(p.box, (sko[0], sko[1], sko[2], sko[3])):
                out.append(Finding("ERROR", "island-purity",
                                   f"{p.ref} is on the sensor island - only "
                                   f"{sorted(allowed)} may be"))

    # --- every part placed exactly once ------------------------------------
    refs = [p.ref for p in placed]
    if len(refs) != len(set(refs)):
        out.append(Finding("ERROR", "duplicate", "a reference is placed twice"))
    missing = set(PART_BY_REF) - set(refs)
    if missing:
        out.append(Finding("ERROR", "unplaced",
                           f"not placed: {', '.join(sorted(missing))}"))
    return out
