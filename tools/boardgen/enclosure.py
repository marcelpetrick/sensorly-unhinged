# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Parametric enclosure model, derived from the board.

The enclosure is part of the instrument, not packaging: `docs/45-thermal-model.md`
shows Variant B's coupling swinging between 0.13 and 0.43 purely on how well the
sensor chamber breathes. So the case is generated from the same model as the
boards - outline, sensor position, antenna keep-out and connector positions are
read, never retyped - and checked before any geometry is written.

This module produces the numbers and the checks. `mechanical/env-sensor-case.scad`
turns them into solids.

    python -m tools.boardgen.enclosure          # report
    python -m tools.boardgen.enclosure --write  # params + SVG sections
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import geometry as G
from .design import PART_BY_REF
from .place import place
from .variants import (B_BODY_H, B_ISLAND_RECT, B_NECK_RECT, Variant, VARIANTS,
                       antenna_keepout, sensor_keepout)

ROOT = Path(__file__).resolve().parents[2]

# --- printed-part parameters ----------------------------------------------
WALL = 2.0                # side walls
FLOOR = 2.0               # below the battery bay
LID = 2.0
CLEAR_XY = 0.6            # board edge to inner wall
BOARD_T = 1.6
RIB_W = 1.6               # board support ribs
HOLDDOWN_D = 2.2          # lid hold-down pillar diameter
VENT_W = 1.2              # vent slot width
VENT_GAP = 1.4            # material between slots
FILLET = 1.5
TOL = 0.35                # printing tolerance on cut-outs

# Battery: a protected 1S LiPo pouch. 503035 (~500 mAh) is the planning cell
# (EDS-3). The case is allowed to be larger in plan than the PCB to hold it -
# M-01 already expects a 40-45 mm case around a 30 mm board.
BATT_X, BATT_Y, BATT_Z = 35.0, 30.0, 5.0
BATT_CLEAR = 1.0

# The battery connector is the tallest thing on the board by a factor of three,
# so it alone sets the case height. Both options are modelled so the trade is a
# number rather than an opinion.
CONNECTORS = {
    "PH": (7.50, "JST PH 2.0 mm, S2B-PH-SM4-TB - as designed"),
    "SH": (3.40, "JST SH 1.0 mm, SM02B-SRSS-TB - Rev 2 candidate"),
}

# --- component heights above the PCB --------------------------------------
# Every one of these is a real number from a real source, or explicitly TBC.
HEIGHTS = {
    "U1": (2.40, "ESP32-C6-MINI-1 datasheet v1.5 S10.1, 13.2 x 16.6 x 2.4"),
    "J1": (3.16, "HRO TYPE-C-31-M-12, 8.94 x 7.35 x 3.16"),
    "J2": (7.50, "JST PH series, S2B-PH-SM4-TB overall profile height"),
    # J2 is overridden by the `connector` argument to build()
    "L1": (1.20, "Murata DFE201612E, 2.0 x 1.6 x 1.2"),
    "SW1": (3.50, "Panasonic EVQ-PU tactile - TBC against the datasheet"),
    "C1": (1.45, "0805 MLCC, typical maximum"),
    "C9": (1.45, "0805 MLCC, typical maximum"),
    "C10": (1.45, "0805 MLCC, typical maximum"),
    "C11": (1.45, "0805 MLCC, typical maximum"),
    "U4": (1.00, "VQFN-16 3x3, typical maximum"),
    "U2": (0.50, "SHT4x DFN, 1.5 x 1.5 x 0.5"),
}
DEFAULT_H = 1.0           # everything else: 0402/0603, SOT-23, SON


@dataclass
class Cutout:
    name: str
    wall: str              # "left" | "right" | "top" | "bottom" | "lid"
    cx: float              # board coordinates of the part it serves
    cy: float
    width: float
    height: float
    z: float               # above the board's top face
    ref: str


@dataclass
class Case:
    variant: str
    inner_w: float
    inner_h: float
    outer_w: float
    outer_h: float
    board_z: float         # board underside above the inner floor
    top_clear: float
    inner_z: float
    outer_z: float
    tallest: tuple[str, float]
    cutouts: list[Cutout] = field(default_factory=list)
    vents: list[tuple[float, float, float, float]] = field(default_factory=list)
    divider_y: float | None = None
    side_vents: list[tuple[float, float, float]] = field(default_factory=list)
    holddowns: list[tuple[float, float, float]] = field(default_factory=list)
    neck_slot: tuple[float, float] | None = None
    batt_bay: tuple[float, float, float, float] | None = None
    antenna_free: float = 0.0
    connector: str = "PH"
    vent_wall: str = "bottom"


def _height(ref: str) -> float:
    return HEIGHTS.get(ref, (DEFAULT_H, ""))[0]


def _free_spot(v: Variant, boxes, target, d: float, y_max: float | None = None):
    """Nearest point to `target` with `d` mm of bare board, inside the outline."""
    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    for r in range(0, 40):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                x, y = target[0] + dx * 0.5, target[1] + dy * 0.5
                box = (x - d / 2, x + d / 2, y - d / 2, y + d / 2)
                if not G.box_inside_polys(box, v.polys, margin=0.5):
                    continue
                if ay0 <= y <= ay1:
                    continue        # nothing dense behind the antenna (M-04)
                if y_max is not None and y > y_max:
                    continue        # never on the sensor side of the wall
                if any(G.boxes_overlap(box, b, 0.25) for b in boxes):
                    continue
                return x, y
    return None


def build(v: Variant, connector: str = "PH") -> Case:
    placed = {p.ref: p for p in place(v)}
    h_conn = CONNECTORS[connector][0]

    def height(ref: str) -> float:
        return h_conn if ref == "J2" else _height(ref)

    tall_ref = max((p.ref for p in placed.values()
                    if not p.ref.startswith("TP")), key=height)
    tall_h = height(tall_ref)

    top_clear = tall_h + 0.6
    board_z = BATT_Z + BATT_CLEAR          # battery bay under the board
    inner_z = board_z + BOARD_T + top_clear

    # The cavity holds the board *and* the cell, so it is the larger of the two
    # in plan. Sizing it to the PCB alone was the mistake that made the planning
    # cell not fit.
    inner_w = max(v.width + 2 * CLEAR_XY, BATT_X + 2 * BATT_CLEAR)
    inner_h = max(v.height + 2 * CLEAR_XY, BATT_Y + 2 * BATT_CLEAR)

    case = Case(
        variant=v.key,
        inner_w=inner_w, inner_h=inner_h,
        outer_w=inner_w + 2 * WALL, outer_h=inner_h + 2 * WALL,
        board_z=board_z, top_clear=top_clear,
        inner_z=inner_z, outer_z=inner_z + FLOOR + LID,
        tallest=(tall_ref, tall_h),
    )

    # --- cut-outs, positioned from the parts themselves --------------------
    j1, j2 = placed["J1"], placed["J2"]
    case.cutouts.append(Cutout("USB-C", "left", j1.x, j1.y,
                               9.2 + TOL, height("J1") + TOL, 0.0, "J1"))
    case.cutouts.append(Cutout("battery wire", "right", j2.x, j2.y,
                               6.0 + TOL, 4.0, 1.0, "J2"))
    sw, d1 = placed["SW1"], placed["D1"]
    case.cutouts.append(Cutout("button", "lid", sw.x, sw.y, 4.0, 4.0, 0.0, "SW1"))
    case.cutouts.append(Cutout("status LED", "lid", d1.x, d1.y,
                               2.0, 2.0, 0.0, "D1"))

    # --- vents, over the sensor -------------------------------------------
    if v.key == "b":
        ix0, iy0, ix1, iy1 = B_ISLAND_RECT
        vent_area = (ix0 + 1.5, iy0 + 1.5, ix1 - 1.5, iy1 - 1.5)
        nx0, ny0, nx1, ny1 = B_NECK_RECT
        # B_NECK_RECT includes a 0.5 mm electrical-rule overlap onto the body.
        # The physical wall must start beyond the full-width PCB, not there.
        case.divider_y = B_BODY_H + TOL + WALL / 2
        case.neck_slot = (nx1 - nx0 + 2 * TOL, BOARD_T + 2 * TOL)
    else:
        sx0, sx1, sy0, sy1 = sensor_keepout(v)
        vent_area = (sx0 + 1.0, sy0 + 1.0, sx1 - 1.0, v.height - 1.5)
    x0, y0, x1, y1 = vent_area
    n = max(1, int((y1 - y0) // (VENT_W + VENT_GAP)))
    for i in range(n):
        vy = y0 + i * (VENT_W + VENT_GAP)
        case.vents.append((x0, vy, x1 - x0, VENT_W))

    # --- side vents, so the sensor chamber breathes sideways too -----------
    # M-03 wants ambient air at the sensor with a small dead volume. Slots in
    # the lid alone leave the chamber a cup; the wall nearest the sensor gets
    # slots as well.
    s_ref = placed["U2"]
    vent_wall = "bottom" if s_ref.y > v.height / 2 else "top"
    span = 12.0
    n_side = int(span // (VENT_W + VENT_GAP))
    for i in range(n_side):
        cx = s_ref.x - span / 2 + i * (VENT_W + VENT_GAP) + VENT_W / 2
        case.side_vents.append((cx, VENT_W, 3.0))
    case.vent_wall = vent_wall

    # --- lid hold-downs ----------------------------------------------------
    # The board rests on ribs; without something pressing on it, it rattles.
    # Short pillars come down from the lid onto bare board - found by searching
    # for free space, not by assuming a corner is empty.
    # A pillar on the sensor side of the chamber wall would be a plastic
    # thermal bridge straight into the island - the one thing Variant B exists
    # to avoid. Hold-downs live in the electronics chamber only.
    #
    # They also walk the board perimeter rather than aiming at the middle: on a
    # board this dense the interior has no 2.5 mm of bare copper anywhere, but
    # the edge band usually does.
    body_h = B_NECK_RECT[1] if v.key == "b" else v.height
    # On B, body_h *is* the chamber wall, so keep clear of the wall itself too.
    y_max = (body_h - (HOLDDOWN_D / 2 + WALL + 0.5) if v.key == "b"
             else body_h - 1.5)
    boxes = [p.box for p in placed.values()]
    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    perimeter = []
    step = 1.0
    n = int(body_h / step)
    for i in range(n):
        y = 1.6 + i * step
        perimeter += [(1.6, y), (v.width - 1.6, y)]
    for i in range(int(v.width / step)):
        x = 1.6 + i * step
        perimeter += [(x, body_h - 1.6), (x, ay1 + 1.6)]
    for sep, dia in ((9.0, HOLDDOWN_D), (6.0, 1.8)):
        for (px, py) in perimeter:
            if len(case.holddowns) >= 4:
                break
            if any(math.hypot(px - hx, py - hy) < sep
                   for hx, hy, _ in case.holddowns):
                continue
            spot = _free_spot(v, boxes, (px, py), dia, y_max=y_max)
            if spot and math.hypot(spot[0] - px, spot[1] - py) < 1.0:
                case.holddowns.append((spot[0], spot[1], dia))
                boxes.append((spot[0] - dia / 2, spot[0] + dia / 2,
                              spot[1] - dia / 2, spot[1] + dia / 2))
        if len(case.holddowns) >= 3:
            break

    # --- battery bay -------------------------------------------------------
    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    sx0, sx1, sy0, sy1 = sensor_keepout(v)
    bay_y0 = ay1 + 1.0                       # never under the antenna
    if v.key == "b":
        # Stop the cell at the chamber wall: nothing warm belongs on the
        # sensor side of it, least of all a battery (M-07).
        bay_y1 = B_NECK_RECT[1] - 1.0
    else:
        bay_y1 = sy0 - 1.0                   # never under the sensor
    # The bay may use the full cavity, which is wider than the board.
    bay_x0 = (v.width - inner_w) / 2 + 1.0
    bay_x1 = bay_x0 + inner_w - 2.0
    case.batt_bay = (bay_x0, bay_y0, bay_x1, bay_y1)
    case.connector = connector

    # --- antenna clearance the finished case actually provides -------------
    # Free space beyond the antenna: the wall, then air. Requirement M-04 is
    # about metal and dense material; what we can state is how far the nearest
    # solid feature is.
    case.antenna_free = WALL + CLEAR_XY

    return case


# --------------------------------------------------------------------------
def check(v: Variant, c: Case) -> list[str]:
    placed = {p.ref: p for p in place(v)}
    out: list[str] = []

    if c.top_clear < c.tallest[1]:
        out.append(f"top clearance {c.top_clear} < tallest part "
                   f"{c.tallest[0]} at {c.tallest[1]} mm")
    if WALL < 1.6:
        out.append(f"wall {WALL} mm is below the printable minimum")
    if VENT_W < 0.8:
        out.append(f"vent slot {VENT_W} mm will bridge when printed")

    # cut-outs must line up with the parts they are for
    for co in c.cutouts:
        p = placed[co.ref]
        if abs(p.x - co.cx) > 0.01 or abs(p.y - co.cy) > 0.01:
            out.append(f"{co.name} cut-out is not on {co.ref}")

    # battery must not sit under the antenna or under the sensor
    bx0, by0, bx1, by1 = c.batt_bay
    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    if by0 < ay1:
        out.append("battery bay reaches under the antenna keep-out")
    s = placed["U2"]
    if bx0 <= s.x <= bx1 and by0 <= s.y <= by1:
        out.append("battery bay sits under the sensor")

    # vents have to be over the sensor, not somewhere decorative
    if not any(vx <= s.x <= vx + vw and vy - 2 <= s.y <= vy + vh + 6
               for vx, vy, vw, vh in c.vents):
        out.append("no vent slot lies over the sensor")
    if not c.side_vents:
        out.append("the sensor chamber has no side vents")
    if len(c.holddowns) < 2:
        out.append(f"only {len(c.holddowns)} lid hold-down pillar(s) fit - "
                   f"the electronics chamber has no bare board left. The board "
                   f"needs a different retention scheme; see the note below")
    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    for hx, hy, d in c.holddowns:
        if ay0 <= hy <= ay1:
            out.append("a hold-down pillar sits behind the antenna (M-04)")
        if c.divider_y is not None and abs(hy - c.divider_y) < (d / 2 + WALL):
            out.append("a hold-down pillar clashes with the chamber divider")
        if hy > (c.divider_y or 1e9):
            out.append("a hold-down pillar is on the sensor side of the wall")

    if v.key == "b":
        if c.divider_y is None:
            out.append("Variant B has no chamber divider")
        elif not (B_NECK_RECT[1] - 1 <= c.divider_y <= B_NECK_RECT[3] + 1):
            out.append("chamber divider is not at the neck")
        if c.neck_slot and c.neck_slot[0] < (B_NECK_RECT[2] - B_NECK_RECT[0]):
            out.append("neck slot is narrower than the neck")
        if c.divider_y is not None and (
                c.divider_y - WALL / 2 < B_BODY_H + TOL - 1e-9 or
                c.divider_y + WALL / 2 > B_ISLAND_RECT[1] - TOL + 1e-9):
            out.append("chamber divider intersects the PCB body or island")

    # E-02 asks for 500-1000 mAh. Report what the bay can actually hold.
    if not planning_cell_fits(c):
        out.append("the actual 35 x 30 x 5 mm planning cell does not fit the battery bay")
    if fitted_mah(c) < 500:
        out.append(f"battery bay {bx1 - bx0:.0f} x {by1 - by0:.0f} x "
                   f"{BATT_Z:.0f} mm holds about {fitted_mah(c):.0f} mAh, "
                   f"below requirement E-02's 500 mAh minimum")
    return out


# 1S LiPo pouch cells run about 90 mAh per cm3 of overall volume - calibrated
# against the 503035 (5.25 cm3, 500 mAh) used as the planning cell.
MAH_PER_CM3 = 90.0


def fitted_mah(c: Case) -> float:
    """Volume proxy only: neither an available pack nor a rated capacity."""
    bx0, by0, bx1, by1 = c.batt_bay
    return (bx1 - bx0) * (by1 - by0) * BATT_Z / 1000.0 * MAH_PER_CM3


def planning_cell_fits(c: Case) -> bool:
    x0, y0, x1, y1 = c.batt_bay
    width, length = x1 - x0, y1 - y0
    return any(x + 2 * BATT_CLEAR <= width and y + 2 * BATT_CLEAR <= length
               for x, y in ((BATT_X, BATT_Y), (BATT_Y, BATT_X)))


# --------------------------------------------------------------------------
def scad_params(v: Variant, c: Case) -> str:
    placed = {p.ref: p for p in place(v)}
    lines = ["// SPDX-FileCopyrightText: 2026 Marcel Petrick "
             "<mail@marcelpetrick.it>",
             "// SPDX-License-Identifier: GPL-3.0-or-later",
             f"// Generated by tools/boardgen/enclosure.py for variant "
             f"{v.key.upper()} ({v.name}). Do not edit.",
             f"variant = \"{v.key}\";",
             f"board_w = {v.width}; board_h = {v.height}; board_t = {BOARD_T};",
             f"wall = {WALL}; floor_t = {FLOOR}; lid_t = {LID};",
             f"clear_xy = {CLEAR_XY}; fillet = {FILLET}; tol = {TOL};",
             f"rib_w = {RIB_W};",
             f"inner_w = {c.inner_w}; inner_h = {c.inner_h}; inner_z = {c.inner_z};",
             f"board_z = {c.board_z}; top_clear = {c.top_clear};",
             f"outer_w = {c.outer_w}; outer_h = {c.outer_h}; outer_z = {c.outer_z};",
             f"batt = [{BATT_X}, {BATT_Y}, {BATT_Z}];",
             "// battery bay in BOARD coordinates; it may extend past the",
             "// board edge, because the cavity is sized to the cell, not the PCB",
             f"batt_bay = [{c.batt_bay[0]}, {c.batt_bay[1]}, "
             f"{c.batt_bay[2]}, {c.batt_bay[3]}];",
             f"divider_y = {c.divider_y if c.divider_y is not None else -1};",
             f"neck_slot = [{c.neck_slot[0] if c.neck_slot else 0}, "
             f"{c.neck_slot[1] if c.neck_slot else 0}];"]
    ao = antenna_keepout(v)
    lines.append(f"antenna_keepout = [{ao[0]}, {ao[2]}, {ao[1]}, {ao[3]}];")
    lines.append("// [x, y, w, h] on the board, in board coordinates")
    lines.append("vents = [" + ", ".join(
        f"[{x}, {y}, {w}, {h}]" for x, y, w, h in c.vents) + "];")
    lines.append(f'vent_wall = "{c.vent_wall}";')
    lines.append("// [centre, width, height] on the sensor-chamber wall")
    lines.append("side_vents = [" + ", ".join(
        f"[{x}, {w}, {h}]" for x, w, h in c.side_vents) + "];")
    lines.append("// [x, y, diameter] hold-down pillars, board coordinates")
    lines.append("holddowns = [" + ", ".join(
        f"[{x}, {y}, {d}]" for x, y, d in c.holddowns) + "];")
    lines.append("// [wall, x, y, width, height, z] - x,y in board coordinates")
    lines.append("cutouts = [" + ", ".join(
        f'["{co.wall}", {co.cx}, {co.cy}, {co.width}, {co.height}, {co.z}]'
        for co in c.cutouts) + "];")
    lines.append("board_outline = [" + ", ".join(
        f"[{x}, {y}]" for x, y in v.outline) + "];")
    return "\n".join(lines) + "\n"


def report() -> str:
    o = ["# 80 — Enclosure (generated)", "",
         "<!-- Generated by `make mech` from tools/boardgen/enclosure.py. -->", "",
         "The case is derived from the board model: outline, sensor position,",
         "antenna keep-out and every connector position are read from it, never",
         "retyped. `mechanical/env-sensor-case.scad` turns these numbers into",
         "solids.", "",
         "The lid uses a perimeter locating ring. Hold-down reach is measured",
         "from the lid seating face, not from the ring tip; `make mech` checks",
         "the full XYZ mesh extent to catch PCB interference.", "",
         "Variant B's divider lies wholly inside the physical neck span, with",
         "printing clearance from the body and island; the electrical rule",
         "zone boundary is not used as a mechanical wall position.", "",
         "## Component heights", "",
         "| Ref | Height | Source |", "|---|---:|---|"]
    for ref, (h, src) in sorted(HEIGHTS.items(), key=lambda kv: -kv[1][0]):
        o.append(f"| {ref} | {h:.2f} mm | {src} |")
    o += ["", "## Result", "",
          "| | Variant A | Variant B |", "|---|---:|---:|"]
    cases = {k: build(v) for k, v in VARIANTS.items()}
    alt = {k: build(v, "SH") for k, v in VARIANTS.items()}
    rows = [
        ("Outer size (mm)", lambda c: f"{c.outer_w:.1f} × {c.outer_h:.1f} × {c.outer_z:.1f}"),
        ("Internal cavity height", lambda c: f"{c.inner_z:.1f} mm"),
        ("Battery bay below board", lambda c: f"{BATT_Z:.1f} mm"),
        ("Clearance above board", lambda c: f"{c.top_clear:.1f} mm"),
        ("Tallest part", lambda c: f"{c.tallest[0]} at {c.tallest[1]:.2f} mm"),
        ("Largest cell the bay holds", lambda c:
         f"{c.batt_bay[2] - c.batt_bay[0]:.0f} × "
         f"{c.batt_bay[3] - c.batt_bay[1]:.0f} × {BATT_Z:.0f} mm"),
        ("Volume proxy, NOT rated pack capacity", lambda c: f"{fitted_mah(c):.0f} mAh equivalent"),
        ("Planning cell fits with clearance", lambda c: "yes" if planning_cell_fits(c) else "NO"),
        ("Vent slots over the sensor", lambda c:
         f"{len(c.vents)} in the lid + {len(c.side_vents)} in the wall"),
        ("Lid hold-down pillars", lambda c: f"{len(c.holddowns)}"),
        ("Chambers", lambda c: "2, divided at the neck" if c.divider_y else "1"),
        ("Solid material beyond the antenna", lambda c: f"{c.antenna_free:.1f} mm"),
    ]
    for label, f in rows:
        o.append(f"| {label} | {f(cases['a'])} | {f(cases['b'])} |")
    o += ["",
          "## The battery connector sets the case height", "",
          "| Battery connector | Height above PCB | Variant A case | Variant B case |",
          "|---|---:|---:|---:|"]
    for key, (h, desc) in CONNECTORS.items():
        ca, cb = build(VARIANTS["a"], key), build(VARIANTS["b"], key)
        o.append(f"| {desc} | {h:.2f} mm | {ca.outer_z:.1f} mm | {cb.outer_z:.1f} mm |")
    o += ["",
          f"Requirement M-01 asks for a case 13-18 mm thick. As designed it is "
          f"**{cases['a'].outer_z:.1f} mm** - the JST PH battery header alone is "
          f"{CONNECTORS['PH'][0]:.1f} mm, three times the height of the radio "
          f"module, and it sets the whole cavity. Moving to a 1.0 mm-pitch JST SH "
          f"brings the case to **{alt['a'].outer_z:.1f} mm**, inside the "
          f"requirement, at the cost of a fiddlier connector to mate by hand.",
          "",
          "That is the honest shape of the trade: *user-replaceable battery* is "
          "not free, and on a device this small the connector, not the cell, is "
          "what you pay in. Recorded as a Rev 2 item; Rev 1 keeps the PH because "
          "a connector you can actually plug in at the bench is worth 4 mm while "
          "we are still bringing boards up.", ""]
    o += ["## Board retention, and a decision coming back around", "",
          f"The board rests on four ribs and is meant to be pinned by short "
          f"pillars from the lid onto bare copper-free board. The generator "
          f"searches the placement for room rather than assuming a corner is "
          f"empty, and finds **{len(cases['a'].holddowns)} on Variant A** but "
          f"only **{len(cases['b'].holddowns)} on Variant B** - B's electronics "
          f"chamber carries all 41 parts in a narrower body, and there is no "
          f"bare board left.", "",
          "The first attempt put two of B's pillars *on the sensor island*: "
          "plastic bridging the lid straight into the thermally isolated part, "
          "which would have quietly wrecked the experiment the island exists "
          "for. That is now a hard check.", "",
          "The real fix is two M2 nylon screws through the lid into bosses - "
          "and the board has no holes for them, because `40-floorplans.md` "
          "decided against mounting holes on the grounds that M-04 forbids "
          "metal near the antenna and a nylon boss costs 19 mm² of a 1000 mm² "
          "board. That was a reasonable call in the PCB phase and it is now a "
          "retention problem in the mechanical phase. Nylon screws are not "
          "metal; the antenna objection does not actually apply to them. **Rev 2 "
          "should carry two nylon M2 holes in the electronics chamber**, which "
          "costs a little copper and solves this cleanly.", "",
          "## The battery does not fit, and that is a finding", "",
          f"Requirement E-02 asks for 500-1000 mAh. The bay in Variant A holds "
          f"about **{fitted_mah(cases['a']):.0f} mAh** and Variant B about "
          f"**{fitted_mah(cases['b']):.0f} mAh**, because the cell may sit "
          f"neither under the antenna keep-out nor under the sensor, and what "
          f"is left is a strip.", "",
          "These mAh figures are only a volume-density proxy. No compatible",
          "protected pack of that capacity has been selected or demonstrated to",
          "fit. They must not enter a runtime claim or purchasing BOM.", "",
          "EDS-3 remains open: select one actual protected pack for both variants,",
          "including connector, lead bend radius, swelling allowance and insulation.",
          "The current planning cell fails the dimension check. Validate support",
          "ribs and retention against the actual cell, then print and assemble both",
          "cases before closing the mechanical release gate. Case dimensions alone",
          "do not prove battery fit or safe retention.", ""]
    for k, v in VARIANTS.items():
        probs = check(v, cases[k])
        o.append(f"**Variant {k.upper()} checks:** "
                 + ("all pass" if not probs else "")
                 )
        for p in probs:
            o.append(f"- ⚠️ {p}")
        o.append("")
    return "\n".join(o)


if __name__ == "__main__":
    print(report())
    if "--write" in sys.argv:
        d = ROOT / "mechanical"
        d.mkdir(exist_ok=True)
        for k, v in VARIANTS.items():
            (d / f"params-{k}.scad").write_text(scad_params(v, build(v)))
            (d / f"case-{k}.scad").write_text(
                f"// SPDX-FileCopyrightText: 2026 Marcel Petrick "
                f"<mail@marcelpetrick.it>\n"
                f"// SPDX-License-Identifier: GPL-3.0-or-later\n"
                f"// Generated wrapper for variant {k.upper()}. "
                f"Edit env-sensor-case.scad or the generator, not this file.\n"
                f'include <params-{k}.scad>\n'
                f'include <env-sensor-case.scad>\n')
        (ROOT / "docs" / "80-enclosure.md").write_text(report() + "\n")
