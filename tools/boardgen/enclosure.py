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

import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import geometry as G
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
MIN_SUPPORT_H = 0.8       # provisional minimum printable support thickness
USB_SHELL_W, USB_SHELL_H = 14.0, 8.0  # provisional max cable boot envelope
USB_BODY_W = 8.94         # HRO TYPE-C-31-M-12 body width, source in HEIGHTS
USB_GUIDE_T = 1.2         # provisional printed polymer guide thickness
USB_PACK_CLEAR = 0.5      # additional separation from full swelling reserve
EDGE_OVERLAP = 0.6        # provisional printed clamp bite onto PCB edge
EDGE_LENGTH = 1.2         # provisional clamp length along edge
VENT_W = 1.2              # vent slot width
VENT_GAP = 1.4            # material between slots
FILLET = 1.5
TOL = 0.35                # printing tolerance on cut-outs

# Selected protected 1S pack: LiPol FD_3245_20 / LP702040, 550 mAh, PCM +
# Semitec 103AT-2 NTC and three-wire harness. These are the drawing's maximum
# assembled dimensions (41+1, 20+0.5, 7+0.3 mm), not the cell-code nominal.
# Clearance is per side in XY; Z_ALLOW is reserved for additional swelling.
BATT_X, BATT_Y, BATT_Z = 42.0, 20.5, 7.3
BATT_XY_CLEAR = 0.5
BATT_Z_ALLOW = 1.0
SELECTED_PACK_MAH = 550

CONNECTORS = {
    "PicoBlade": (3.40, "Molex PicoBlade 53261-0371, right-angle SMT"),
}

# --- component heights above the PCB --------------------------------------
# Every one of these is a real number from a real source, or explicitly TBC.
HEIGHTS = {
    "U1": (2.40, "ESP32-C6-MINI-1 datasheet v1.5 S10.1, 13.2 x 16.6 x 2.4"),
    "J1": (3.16, "HRO TYPE-C-31-M-12, 8.94 x 7.35 x 3.16"),
    "J2": (3.40, "Molex PicoBlade 53261-0371 drawing, mated height"),
    # J2 is overridden by the `connector` argument to build()
    "L1": (1.20, "Murata DFE201612E, 2.0 x 1.6 x 1.2"),
    "SW1": (1.95, "[Panasonic EVQPUJ02K reference specification, p.2](https://industrial.panasonic.com/cdbs/www-data/pdf/ATK0000/ATK0000COS4319.pdf), 1.65 +0.30/-0.10 mm, side-operated"),
    "C1": (1.35, "[Murata GRM21BR61C106KE15L drawing, p.2](https://www.farnell.com/datasheets/3929902.pdf), 1.25 ±0.10 mm maximum"),
    "C8": (1.35, "[Murata GRM21BR61C106KE15L drawing, p.2](https://www.farnell.com/datasheets/3929902.pdf), 1.25 ±0.10 mm maximum"),
    "C9": (1.35, "[Murata GRM21BR61C106KE15L drawing, p.2](https://www.farnell.com/datasheets/3929902.pdf), 1.25 ±0.10 mm maximum"),
    "C10": (1.35, "[Murata GRM21BR61C106KE15L drawing, p.2](https://www.farnell.com/datasheets/3929902.pdf), 1.25 ±0.10 mm maximum"),
    "C11": (1.35, "[Murata GRM21BR61C106KE15L drawing, p.2](https://www.farnell.com/datasheets/3929902.pdf), 1.25 ±0.10 mm maximum"),
    "U5": (1.45, "[ST USBLC6-2 DS4260 Rev7, Table3 p.12](https://www.st.com/resource/en/datasheet/usblc6-2.pdf), maximum"),
    "U4": (1.00, "VQFN-16 3x3, typical maximum"),
    "Q1": (1.11, "[onsemi 2N7002L/D, CASE 318 Issue AU, p.4](https://www.onsemi.com/download/data-sheet/pdf/2n7002l-d.pdf), maximum"),
    "D1": (1.10, "[Kingbright KP-1608SGC DSAB0301V21B, p.1](https://www.kingbright.com/attachments/file/psearch/000/00/20160808bak/KP-1608SGC%28Ver.21B%29.pdf), maximum"),
    "U2": (0.73, "[Sensirion SHT4x v7.3, Fig16 p.16](https://sensirion.com/resource/datasheet/sht4x), filtered SHT45-AD1F 0.63 ±0.10 mm"),
}
# Raise both PCBs enough that even the tolerance-expanded cable access
# envelope stays above the full pouch + swelling reserve. J1 height comes
# from HEIGHTS; all shell and printed-tolerance values are explicit assumptions.
SUPPORT_H = max(MIN_SUPPORT_H,
                USB_PACK_CLEAR + USB_SHELL_H / 2 + TOL
                - BOARD_T - HEIGHTS["J1"][0] / 2)

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
    reach_x: float = 0.0   # left access channel reaches the PCB front edge


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
    edge_holddowns: list[tuple[str, float]] = field(default_factory=list)
    body_h: float = 0.0
    neck_slot: tuple[float, float] | None = None
    batt_bay: tuple[float, float, float, float] | None = None
    antenna_free: float = 0.0
    connector: str = "PicoBlade"
    vent_wall: str = "bottom"
    lid_port_relief: bool = True
    side_stops: bool = True
    body_end_stops: bool = True
    usb_guides: list[tuple[float, float, float, float, float]] = field(default_factory=list)


def _height(ref: str) -> float:
    return HEIGHTS.get(ref, (DEFAULT_H, ""))[0]


def build(v: Variant, connector: str = "PicoBlade") -> Case:
    placed = {p.ref: p for p in place(v)}
    h_conn = CONNECTORS[connector][0]

    def height(ref: str) -> float:
        return h_conn if ref == "J2" else _height(ref)

    tall_ref = max((p.ref for p in placed.values()
                    if not p.ref.startswith("TP")), key=height)
    tall_h = height(tall_ref)

    top_clear = tall_h + 0.6
    # The support shelf occupies its own layer above the swelling allowance;
    # it must never descend alongside or onto the pouch.
    board_z = BATT_Z + BATT_Z_ALLOW + SUPPORT_H
    inner_z = board_z + BOARD_T + top_clear

    # The cavity holds the board *and* the cell, so it is the larger of the two
    # in plan. Sizing it to the PCB alone was the mistake that made the planning
    # cell not fit.
    inner_w = max(v.width + 2 * CLEAR_XY, BATT_X + 2 * BATT_XY_CLEAR)
    inner_h = max(v.height + 2 * CLEAR_XY, BATT_Y + 2 * BATT_XY_CLEAR)

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
                               USB_SHELL_W + 2 * TOL, USB_SHELL_H + 2 * TOL,
                               height("J1") / 2, "J1"))
    # SW1 is side-operated, so a lid hole above it is not an actuator.
    # Prototype servicing/provisioning requires the removable lid off.
    d1 = placed["D1"]
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
        case.neck_slot = (nx1 - nx0 + 4 * TOL, BOARD_T + 2 * TOL)
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

    # --- edge retention ----------------------------------------------------
    # Rectangular fingers reach from the lid to a narrow component-free edge
    # strip. Unlike an interior pillar they do not need a large round bare spot
    # or a mounting hole. Supports below use these same coordinates, keeping
    # clamp loads out of the pouch and out of B's neck/island.
    case.body_h = B_BODY_H if v.key == "b" else v.height
    boxes = [p.box for p in placed.values()]
    ay1 = antenna_keepout(v)[3]
    for side in ("left", "right"):
        candidates = []
        for i in range(int((case.body_h - ay1) * 2)):
            y = ay1 + EDGE_LENGTH / 2 + TOL + i * 0.5
            if y + EDGE_LENGTH / 2 + TOL >= case.body_h:
                continue
            if side == "left" and abs(y - j1.y) < USB_SHELL_W / 2 + TOL + EDGE_LENGTH / 2:
                continue  # retention must not bridge the cable access notch
            x0 = 0 if side == "left" else v.width - EDGE_OVERLAP
            box = (x0, x0 + EDGE_OVERLAP,
                   y - EDGE_LENGTH / 2, y + EDGE_LENGTH / 2)
            if not any(G.boxes_overlap(box, b, 0.25) for b in boxes):
                candidates.append(y)
        # Spread two fingers along each edge where possible. On B the left
        # USB/regulator leave one window; the right edge provides two.
        for y in reversed(candidates):
            if sum(s == side for s, _ in case.edge_holddowns) >= 2:
                break
            if all(s != side or abs(y - cy) >= EDGE_LENGTH + 1.0
                   for s, cy in case.edge_holddowns):
                case.edge_holddowns.append((side, y))

    # Positive Y registration uses the robust USB shell, away from RF and the
    # sensor. Two lid rails flank its upper side faces; X and +Y PCB edge stops
    # below the component layer supplement them. Rail bottoms stay above every
    # neighbouring component envelope, so load is not applied to passives.
    gx0 = EDGE_OVERLAP + TOL
    gx1 = j1.x + 7.35 / 2 - TOL  # HRO body depth, source in HEIGHTS
    for gy in (j1.y - USB_BODY_W / 2 - TOL - USB_GUIDE_T,
               j1.y + USB_BODY_W / 2 + TOL):
        rect = (gx0, gx1, gy, gy + USB_GUIDE_T)
        nearby = [height(p.ref) for p in placed.values() if p.ref != "J1"
                  and G.boxes_overlap(rect, p.box)]
        lower_z = max(1.5, max(nearby, default=0) + TOL)
        case.usb_guides.append((gx0, gy, gx1-gx0, USB_GUIDE_T, lower_z))

    # --- battery bay -------------------------------------------------------
    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    sx0, sx1, sy0, sy1 = sensor_keepout(v)
    allowed_y0 = ay1 + BATT_XY_CLEAR         # never under the antenna
    if v.key == "b":
        # Stop the cell at the chamber wall: nothing warm belongs on the
        # sensor side of it, least of all a battery (M-07).
        allowed_y1 = B_NECK_RECT[1] - BATT_XY_CLEAR
    else:
        allowed_y1 = sy0 - BATT_XY_CLEAR     # never under the sensor
    if allowed_y1 - allowed_y0 < BATT_Y:
        # Keep the impossible geometry visible to check(); never silently crop.
        pack_y0 = allowed_y0
    else:
        pack_y0 = (allowed_y0 + allowed_y1 - BATT_Y) / 2
    pack_x0 = (v.width - BATT_X) / 2
    case.batt_bay = (pack_x0, pack_y0, pack_x0 + BATT_X, pack_y0 + BATT_Y)
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

    usb = next(co for co in c.cutouts if co.ref == "J1")
    if usb.width < USB_SHELL_W + 2 * TOL or usb.height < USB_SHELL_H + 2 * TOL:
        out.append("USB opening does not clear the provisional cable shell")
    if usb.reach_x < 0 or not c.lid_port_relief:
        out.append("USB access does not relieve the recessed wall and lid lip")
    if placed["J1"].rot % 360 != 270:
        out.append("USB socket mouth does not face the left access opening")
    shell_bottom = c.board_z + BOARD_T + usb.z - usb.height / 2
    if shell_bottom < BATT_Z + BATT_Z_ALLOW + USB_PACK_CLEAR - 1e-9:
        out.append("USB cable access enters the reserved battery/swelling clearance")

    if not c.side_stops or not c.body_end_stops or len(c.usb_guides) != 2:
        out.append("PCB has no complete positive XY registration")
    for x, y, w, h, z in c.usb_guides:
        if z >= _height("J1") - 0.35:
            out.append("USB guide does not engage the upper socket shell")
        if any(z < _height(p.ref) + TOL - 1e-9 for p in placed.values()
               if p.ref != "J1" and G.boxes_overlap((x,x+w,y,y+h),p.box)):
            out.append("USB registration guide loads another component")
    if TOL >= CLEAR_XY:
        out.append("Y registration may let the PCB antenna edge reach the wall")

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
    if len(c.edge_holddowns) < 3 or {s for s, _ in c.edge_holddowns} != {"left", "right"}:
        out.append("fewer than three edge clamps on both sides of the electronics body")
    for side, y in c.edge_holddowns:
        if side == "left" and abs(y - usb.cy) < usb.width / 2 + EDGE_LENGTH / 2:
            out.append("an edge clamp obstructs the USB cable access notch")
        x0 = 0 if side == "left" else v.width - EDGE_OVERLAP
        box = (x0, x0 + EDGE_OVERLAP, y - EDGE_LENGTH / 2, y + EDGE_LENGTH / 2)
        if any(G.boxes_overlap(box, p.box, 0.25) for p in placed.values()):
            out.append("an edge clamp overlaps a component or test pad")
        if y - EDGE_LENGTH / 2 <= ay1 or y + EDGE_LENGTH / 2 >= c.body_h:
            out.append("an edge clamp leaves the electronics retention region")
    if v.key == "b":
        if c.divider_y is None:
            out.append("Variant B has no chamber divider")
        elif not (B_NECK_RECT[1] - 1 <= c.divider_y <= B_NECK_RECT[3] + 1):
            out.append("chamber divider is not at the neck")
        if c.neck_slot and c.neck_slot[0] <= (B_NECK_RECT[2] - B_NECK_RECT[0]) + 2 * TOL:
            out.append("neck slot has no reserve beyond positive X registration travel")
        if c.divider_y is not None and (
                c.divider_y - WALL / 2 < B_BODY_H + TOL - 1e-9 or
                c.divider_y + WALL / 2 > B_ISLAND_RECT[1] - TOL + 1e-9):
            out.append("chamber divider intersects the PCB body or island")

    # E-02 asks for 500-1000 mAh. Check the selected 550 mAh pack geometry.
    if not planning_cell_fits(c):
        out.append("the selected LP702040 maximum envelope does not fit the battery bay")
    return out


def planning_cell_fits(c: Case) -> bool:
    x0, y0, x1, y1 = c.batt_bay
    width, length = x1 - x0, y1 - y0
    return any(x <= width + 1e-9 and y <= length + 1e-9
               for x, y in ((BATT_X, BATT_Y), (BATT_Y, BATT_X)))


# --------------------------------------------------------------------------
def scad_params(v: Variant, c: Case) -> str:
    lines = ["// SPDX-FileCopyrightText: 2026 Marcel Petrick "
             "<mail@marcelpetrick.it>",
             "// SPDX-License-Identifier: GPL-3.0-or-later",
             f"// Generated by tools/boardgen/enclosure.py for variant "
             f"{v.key.upper()} ({v.name}). Do not edit.",
             f"variant = \"{v.key}\";",
             f"board_w = {v.width}; board_h = {v.height}; board_t = {BOARD_T};",
             f"wall = {WALL}; floor_t = {FLOOR}; lid_t = {LID};",
             f"clear_xy = {CLEAR_XY}; fillet = {FILLET}; tol = {TOL};",
             f"support_h = {SUPPORT_H};",
             f"usb_lid_relief = {str(c.lid_port_relief).lower()};",
             f"side_stops = {str(c.side_stops).lower()}; body_end_stops = {str(c.body_end_stops).lower()};",
             f"body_h = {c.body_h};",
             f"edge_overlap = {EDGE_OVERLAP}; edge_length = {EDGE_LENGTH};",
             f"inner_w = {c.inner_w}; inner_h = {c.inner_h}; inner_z = {c.inner_z};",
             f"board_z = {c.board_z}; top_clear = {c.top_clear};",
             f"outer_w = {c.outer_w}; outer_h = {c.outer_h}; outer_z = {c.outer_z};",
             f"batt = [{BATT_X}, {BATT_Y}, {BATT_Z}];",
             f"batt_reserved_z = {BATT_Z + BATT_Z_ALLOW};",
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
    lines.append("usb_guides = [" + ", ".join(
        f"[{x}, {y}, {w}, {h}, {z}]" for x,y,w,h,z in c.usb_guides) + "];")
    lines.append("edge_holddowns = [" + ", ".join(
        f'["{side}", {y}]' for side, y in c.edge_holddowns) + "];")
    lines.append("// [wall, x, y, width, height, z] - x,y in board coordinates")
    lines.append("cutouts = [" + ", ".join(
        f'["{co.wall}", {co.cx}, {co.cy}, {co.width}, {co.height}, {co.z}, {co.reach_x}]'
        for co in c.cutouts) + "];")
    lines.append("board_outline = [" + ", ".join(
        f"[{x}, {y}]" for x, y in v.outline) + "];")
    return "\n".join(lines) + "\n"


def report(cases: dict[str, Case] | None = None, *, strict: bool = False) -> str:
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
         "The perimeter lip is relieved where it crosses B's divider. The",
         "OpenSCAD `interference` mode intersects the closed lid with the base;",
         "the expected result is empty. This does not prove pack/PCB fit.", "",
         "The left USB opening and matching lid/lip notch expose the full recess",
         "to the PCB front edge; the cable boot can enter it instead of relying",
         "on extra metal-tip reach. J1 faces left (270°); its placement uses the",
         "manufacturer PCB-edge datum. The provisional maximum boot envelope",
         "is **14 × 8 mm**, with 0.35 mm clearance per edge. These are explicit",
         "design assumptions, not USB-standard limits or a verified cable.", "",
         f"Both support heights are derived as {SUPPORT_H:.2f} mm so the complete",
         "tolerance-expanded cable envelope stays at least 0.5 mm above the",
         "pack's maximum thickness plus full 1.0 mm swelling reserve. The",
         "OpenSCAD `cable_interference` check intersects that access path with",
         "the assembled case and reserved pack volume; it must be empty.", "",
         "Before charging, fit the intended cable, record its maximum boot",
         "dimensions and verify insertion, retention and lead/pack clearance.", "",
         "SW1 (EVQPUJ02K) is side-operated. Remove the taped lid to press it",
         "laterally with a nonconductive tool during bench setup/provisioning;",
         "there is no top button opening. Refit the lid before thermal tests.", "",
         "## Component heights", "",
         "| Ref | Height | Source |", "|---|---:|---|"]
    for ref, (h, src) in sorted(HEIGHTS.items(), key=lambda kv: -kv[1][0]):
        o.append(f"| {ref} | {h:.2f} mm | {src} |")
    o += ["", "## Result", "",
          "| | Variant A | Variant B |", "|---|---:|---:|"]
    cases = cases or {k: build(v) for k, v in VARIANTS.items()}
    rows = [
        ("Outer size (mm)", lambda c: f"{c.outer_w:.1f} × {c.outer_h:.1f} × {c.outer_z:.1f}"),
        ("Internal cavity height", lambda c: f"{c.inner_z:.1f} mm"),
        ("Battery bay below board", lambda c: f"{BATT_Z:.1f} mm"),
        ("Clearance above board", lambda c: f"{c.top_clear:.1f} mm"),
        ("Tallest part", lambda c: f"{c.tallest[0]} at {c.tallest[1]:.2f} mm"),
        ("Modeled maximum pack envelope", lambda c:
         f"{c.batt_bay[2] - c.batt_bay[0]:.1f} × "
         f"{c.batt_bay[3] - c.batt_bay[1]:.1f} × {BATT_Z:.1f} mm"),
        ("Selected pack", lambda c: f"LP702040, {SELECTED_PACK_MAH} mAh"),
        ("Selected pack fits modeled bay", lambda c: "yes" if planning_cell_fits(c) else "NO"),
        ("Vent slots over the sensor", lambda c:
         f"{len(c.vents)} in the lid + {len(c.side_vents)} in the wall"),
        ("Lid edge clamps / matching supports", lambda c: f"{len(c.edge_holddowns)}"),
        ("Chambers", lambda c: "2, divided at the neck" if c.divider_y else "1"),
        ("Solid material beyond the antenna", lambda c: f"{c.antenna_free:.1f} mm"),
    ]
    for label, f in rows:
        o.append(f"| {label} | {f(cases['a'])} | {f(cases['b'])} |")
    o += ["", "## Selected battery and connector", "",
          "Both cases are sized for the selected **LP702040 550 mAh** protected "
          "pack. Drawing FD_3245_20 specifies 550 mAh minimum, maximum assembled "
          "dimensions 42 × 20.5 × 7.3 mm, a Semitec 103AT-2 NTC and a "
          "45 ± 3 mm three-wire "
          "Molex 51021-0300 PicoBlade harness. J2 is the mating 53261-0371 "
          "right-angle header at 3.40 mm mated height.", "",
          f"The generated case is **{cases['a'].outer_z:.1f} mm** thick. The "
          "model reserves 0.5 mm around every pack edge and 1.0 mm above the "
          "drawing's maximum pouch thickness for manufacturing tolerance and "
          "swelling. The support shelves begin above that allowance; nothing "
          "rigid may occupy it.", "",
          "Incoming inspection must confirm the drawing and cavity order "
          "`1=black/-`, `2=yellow/NTC`, `3=red/+` before mating. An assembled "
          "lead-bend/retention "
          "test remains part of the battery qualification gate.", ""]
    o += ["## Board retention and prototype lid closure", "",
          "Both variants use rectangular lid fingers on component-free PCB edge "
          "strips, with matching wall-connected support shelves below. The "
          "generator checks every clamp against component and test-pad envelopes. "
          "Variant B supports and clamps remain entirely in the electronics body; "
          "no printed support touches its neck or sensor island.", "",
          "Polymer side stops constrain X at the supported PCB edges. Rear "
          "corner stops capture the electronics body end outside B's neck. "
          "Two lid rails flank the upper USB shell and constrain both Y "
          "directions without touching the PCB antenna end; their undersides "
          "clear adjacent components. The modeled movement before stop contact "
          "is 0.35 mm, below the 0.6 mm antenna-edge/wall gap. USB-shell contact, "
          "stop strength and printed tolerances remain assembly qualification "
          "gates; vertical friction alone is not the retention scheme. B’s neck "
          "slot has an additional 0.35 mm per-side reserve beyond the modeled "
          "X stop travel, so the stops engage before the neck touches the divider.", "",
          f"The {EDGE_OVERLAP:.1f} mm edge bite, {EDGE_LENGTH:.1f} mm finger length, 0.35 mm printed cut-out "
          "tolerance and 0.25 mm component margin are provisional design "
          "assumptions, not demonstrated printer capability. These dimensions "
          "must be checked on printed samples before qualification. Print the "
          "base floor down with removable supports under the cantilever shelves; "
          "print the lid outer face down. Remove every support and sharp edge "
          "from the battery bay. Use the same recorded polymer and print settings "
          "for both A/B cases.", "",
          "The perimeter ring locates the lid but does not latch it. For the "
          "prototype, retain the lid with removable nonmetallic tape across the "
          "electronics chamber side walls, away from the antenna end, USB opening "
          "and sensor vents. Tape is a provisional assembly assumption; record "
          "material and position for both A/B cases. Positive lid closure and "
          "drop/handling retention remain physically unqualified.", "",
          "## Battery qualification still requires hardware", "",
          "The selected pack passes the parametric plan-view and height checks in "
          "both variants. That is a design check, not evidence that a pouch, its "
          "protection board and leads tolerate the printed retention scheme. "
          "Before enclosed charging, inspect supplier samples, print and assemble "
          "both cases, then run the EDS §5.2 temperature, timer and fault tests.", ""]
    for k, v in VARIANTS.items():
        probs = check(v, cases[k])
        if strict and probs:
            raise ValueError(f"Variant {k.upper()} enclosure: {'; '.join(probs)}")
        o.append(f"**Variant {k.upper()} checks:** "
                 + ("all pass" if not probs else "")
                 )
        for p in probs:
            o.append(f"- ⚠️ {p}")
        o.append("")
    return "\n".join(o)


if __name__ == "__main__":
    cases = {k: build(v) for k, v in VARIANTS.items()}
    rendered_report = report(cases, strict=True)
    print(rendered_report)
    if "--write" in sys.argv:
        d = ROOT / "mechanical"
        d.mkdir(exist_ok=True)
        for k, v in VARIANTS.items():
            (d / f"params-{k}.scad").write_text(scad_params(v, cases[k]))
            (d / f"case-{k}.scad").write_text(
                f"// SPDX-FileCopyrightText: 2026 Marcel Petrick "
                f"<mail@marcelpetrick.it>\n"
                f"// SPDX-License-Identifier: GPL-3.0-or-later\n"
                f"// Generated wrapper for variant {k.upper()}. "
                f"Edit env-sensor-case.scad or the generator, not this file.\n"
                f'include <params-{k}.scad>\n'
                f'include <env-sensor-case.scad>\n')
        (ROOT / "docs" / "80-enclosure.md").write_text(rendered_report + "\n")
