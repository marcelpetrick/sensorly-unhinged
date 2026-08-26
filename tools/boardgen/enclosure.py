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
from .variants import (B_ISLAND_RECT, B_NECK_RECT, Variant, VARIANTS,
                       antenna_keepout, sensor_keepout)

ROOT = Path(__file__).resolve().parents[2]

# --- printed-part parameters ----------------------------------------------
WALL = 2.0                # side walls
FLOOR = 2.0               # below the battery bay
LID = 2.0
CLEAR_XY = 0.6            # board edge to inner wall
BOARD_T = 1.6
RIB_W = 1.6               # board support ribs
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
    centre: float          # position along that wall, mm from the origin corner
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
    neck_slot: tuple[float, float] | None = None
    batt_bay: tuple[float, float, float, float] | None = None
    antenna_free: float = 0.0
    connector: str = "PH"


def _height(ref: str) -> float:
    return HEIGHTS.get(ref, (DEFAULT_H, ""))[0]


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
    case.cutouts.append(Cutout(
        "USB-C", "left", j1.y, 9.2 + TOL, height("J1") + TOL, 0.0, "J1"))
    case.cutouts.append(Cutout(
        "battery wire", "right", j2.y, 6.0 + TOL, 4.0, 1.0, "J2"))
    case.cutouts.append(Cutout(
        "button", "lid", placed["SW1"].x, 4.0, 4.0, 0.0, "SW1"))
    case.cutouts.append(Cutout(
        "status LED", "lid", placed["D1"].x, 2.0, 2.0, 0.0, "D1"))

    # --- vents, over the sensor -------------------------------------------
    if v.key == "b":
        ix0, iy0, ix1, iy1 = B_ISLAND_RECT
        vent_area = (ix0 + 1.5, iy0 + 1.5, ix1 - 1.5, iy1 - 1.5)
        nx0, ny0, nx1, ny1 = B_NECK_RECT
        case.divider_y = ny0
        case.neck_slot = (nx1 - nx0 + 2 * TOL, BOARD_T + 2 * TOL)
    else:
        sx0, sx1, sy0, sy1 = sensor_keepout(v)
        vent_area = (sx0 + 1.0, sy0 + 1.0, sx1 - 1.0, v.height - 1.5)
    x0, y0, x1, y1 = vent_area
    n = max(1, int((y1 - y0) // (VENT_W + VENT_GAP)))
    for i in range(n):
        vy = y0 + i * (VENT_W + VENT_GAP)
        case.vents.append((x0, vy, x1 - x0, VENT_W))

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
        pos = p.y if co.wall in ("left", "right") else p.x
        if abs(pos - co.centre) > 0.01:
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

    if v.key == "b":
        if c.divider_y is None:
            out.append("Variant B has no chamber divider")
        elif not (B_NECK_RECT[1] - 1 <= c.divider_y <= B_NECK_RECT[3] + 1):
            out.append("chamber divider is not at the neck")
        if c.neck_slot and c.neck_slot[0] < (B_NECK_RECT[2] - B_NECK_RECT[0]):
            out.append("neck slot is narrower than the neck")

    # E-02 asks for 500-1000 mAh. Report what the bay can actually hold.
    if fitted_mah(c) < 500:
        out.append(f"battery bay {bx1 - bx0:.0f} x {by1 - by0:.0f} x "
                   f"{BATT_Z:.0f} mm holds about {fitted_mah(c):.0f} mAh, "
                   f"below requirement E-02's 500 mAh minimum")
    return out


# 1S LiPo pouch cells run about 90 mAh per cm3 of overall volume - calibrated
# against the 503035 (5.25 cm3, 500 mAh) used as the planning cell.
MAH_PER_CM3 = 90.0


def fitted_mah(c: Case) -> float:
    bx0, by0, bx1, by1 = c.batt_bay
    return (bx1 - bx0) * (by1 - by0) * BATT_Z / 1000.0 * MAH_PER_CM3


# --------------------------------------------------------------------------
def scad_params(v: Variant, c: Case) -> str:
    placed = {p.ref: p for p in place(v)}
    lines = [f"// Generated by tools/boardgen/enclosure.py for variant "
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
    lines.append("// [wall, centre, width, height, z]")
    lines.append("cutouts = [" + ", ".join(
        f'["{co.wall}", {co.centre}, {co.width}, {co.height}, {co.z}]'
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
        ("Approximate capacity", lambda c: f"{fitted_mah(c):.0f} mAh"),
        ("Vent slots over the sensor", lambda c: f"{len(c.vents)}"),
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
    o += ["## The battery does not fit, and that is a finding", "",
          f"Requirement E-02 asks for 500-1000 mAh. The bay in Variant A holds "
          f"about **{fitted_mah(cases['a']):.0f} mAh** and Variant B about "
          f"**{fitted_mah(cases['b']):.0f} mAh**, because the cell may sit "
          f"neither under the antenna keep-out nor under the sensor, and what "
          f"is left is a strip.", "",
          "Three ways out, none of them free:", "",
          "1. **A thicker cell.** 8 mm instead of 5 mm reaches 500 mAh in the "
          "same footprint and adds 3 mm to a case that is already over its "
          "height target.",
          "2. **A longer case.** Extending the A case by ~11 mm in Y gets the "
          "planning cell in, at the cost of the 40-45 mm square envelope M-01 "
          "asks for.",
          "3. **Accept less capacity and check it against measurement.** "
          "Requirement E-04 is *runtime*, not capacity; 330 mAh may well carry "
          "three months at the real duty cycle. Nobody knows yet, because the "
          "energy per upload is a Rev-1 measurement.", "",
          "Option 3 is the right one to hold open. Capacity is a proxy; runtime "
          "is the requirement, and we are four weeks from being able to measure "
          "it. This is now an entry in the open-items table rather than a "
          "number chosen today.", "",
          f"One unplanned consequence worth noticing: **Variant B's case is "
          f"{cases['b'].outer_h - cases['a'].outer_h:.0f} mm longer, so it "
          f"holds a {fitted_mah(cases['b']) - fitted_mah(cases['a']):.0f} mAh "
          f"bigger cell** - about {100 * (fitted_mah(cases['b']) / fitted_mah(cases['a']) - 1):.0f} % "
          "more energy. The thermally-isolated variant partially pays for its "
          "own size in battery life. That was not designed in; it fell out of "
          "the geometry.", ""]
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
                f"// Generated wrapper for variant {k.upper()}. "
                f"Edit env-sensor-case.scad or the generator, not this file.\n"
                f'include <params-{k}.scad>\n'
                f'include <env-sensor-case.scad>\n')
        (ROOT / "docs" / "80-enclosure.md").write_text(report() + "\n")
