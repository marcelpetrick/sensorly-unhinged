# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The two physical implementations of the one electrical platform.

Variant A  - compact monolithic board.
Variant B  - same electronics block, plus a milled sensor island on a narrow
             FR-4 neck.  The electronics placement is literally the same table;
             only the outline, the sensor position and the thermal rule zones
             differ.  That is deliberate: it makes the A/B experiment a
             comparison of geometry, not of two different designs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Common electronics block, defined once, in a 28.0 x 34.0 mm body frame.
# Placement order follows docs/00-plan.md: antenna, sensor, connectors, charger,
# regulator, bulk caps, module body, buttons, test pads, remaining passives.
# --------------------------------------------------------------------------
BODY_W = 28.0
BODY_H = 34.0

# ref -> (x, y, rotation)   -- mechanically constrained parts, placed by hand
ANCHORED = {
    # 1. antenna first: module hard against the top edge, antenna outward
    "U1":  (14.0, 11.5, 0),
    # 2. connectors - mechanically constrained, must reach an edge.
    #    Both sit on the SIDES, not the bottom: in Variant B the bottom edge is
    #    where the thermal neck leaves the board, and the two variants share
    #    this table.
    "J1":  (5.5, 24.5, 90),      # USB-C, mouth at the left edge
    "J2":  (22.85, 24.5, 90),     # JST-PH 1S LiPo, mouth at the right edge
    # 3. heat sources, as far from the sensor end as the outline allows
    "U4":  (24.4, 10.5, 0),      # charger - 0.40 W worst case, the hot part
    "U3":  (3.4, 10.0, 0),       # buck regulator
    "L1":  (3.4, 13.2, 0),
    # 4. the rest
    "U5":  (15.5, 22.0, 0),      # USB ESD array
    "SW1": (13.7, 28.0, 0),      # provisioning button
    "D1":  (11.3, 22.0, 0),      # status LED
    # I2C pull-ups: anchored, not auto-placed. EDS S3.1 puts them on the MAIN
    # board so their dissipation stays there, and both variants hand the sensor
    # off at the bottom-centre edge, so this is where they belong in both.
    "R3":  (8.0, 31.3, 0),
    "R4":  (10.0, 31.3, 0),
}

# Passives are auto-placed near an anchor; this table says near what, with what
# preferred rotation, and how tightly.  See place.py.
NEAR = {
    "C1": ("U1", 90), "C2": ("U1", 0), "C3": ("U1", 0),
    "R1": ("U1", 90), "C4": ("U1", 90), "C5": ("SW1", 0), "R2": ("D1", 0),
    "C7": ("U3", 90), "C8": ("U3", 90), "R5": ("U3", 90), "R6": ("U3", 90),
    "R7": ("U4", 90), "R8": ("U4", 90), "R9": ("U4", 90), "R10": ("U4", 90),
    "R11": ("U4", 90), "R12": ("U4", 90), "R13": ("U4", 90),
    "C9": ("U4", 90), "C10": ("U4", 90), "C11": ("U4", 90), "C12": ("U4", 90),
    "R16": ("J1", 0), "R17": ("J1", 0), "C14": ("J1", 0),
    "R14": ("J2", 90), "R15": ("J2", 90), "C13": ("J2", 90),
}

# Pogo field: 2.54 mm grid on the bottom side, one contiguous rectangle.
TESTPAD_ORIGIN = (9.0, 19.5)
TESTPAD_COLS = 6
TESTPAD_PITCH = 2.54


@dataclass
class Variant:
    key: str
    name: str
    revision: str
    width: float
    height: float
    body_dx: float                       # electronics block offset in x
    outline: list[tuple[float, float]]
    sensor_xy: tuple[float, float]
    sensor_cap_xy: tuple[float, float]
    keepouts: list[dict] = field(default_factory=list)
    notes: str = ""

    @property
    def polys(self):
        return [self.outline]


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# --------------------------------------------------------------------------
# Variant A - compact
# --------------------------------------------------------------------------
A_W, A_H = 30.0, 34.0
# The electronics block is NOT centred in the wider A outline: the USB-C mouth
# has to stay flush with the left edge in both variants, so A's extra 2 mm of
# width is added on the right, where only the wire-entry JST sits.
A_DX = 0.0

VARIANT_A = Variant(
    key="a",
    name="Compact",
    revision="HW A1",
    width=A_W, height=A_H, body_dx=A_DX,
    outline=_rect(0, 0, A_W, A_H),
    # Bottom-left corner: the furthest point on this outline from the charger.
    sensor_xy=(16.0, 32.3),
    sensor_cap_xy=(19.5, 32.3),
    notes=("Everything on one 30 x 34 mm rectangle. The sensor sits in the "
           "sensor sits on the bottom edge, as far from the connectors and the "
           "charger as a 30 x 34 mm rectangle allows - and the PCB between "
           "them is solid 4-layer copper the whole way."),
)

# --------------------------------------------------------------------------
# Variant B - thermally isolated sensor island
# --------------------------------------------------------------------------
B_W = 28.0
B_BODY_H = 34.0
B_NECK_W = 3.5        # EDS S3.1 - drives the FR-4 term of the neck conductance
B_NECK_L = 8.0        # longer neck = lower conductance, weaker mechanically
B_ISLAND_W = 18.0
B_ISLAND_H = 9.0
B_H = B_BODY_H + B_NECK_L + B_ISLAND_H          # 51.0

_nx0 = (B_W - B_NECK_W) / 2.0
_nx1 = _nx0 + B_NECK_W
_ix0 = (B_W - B_ISLAND_W) / 2.0
_ix1 = _ix0 + B_ISLAND_W
_y0 = B_BODY_H
_y1 = B_BODY_H + B_NECK_L
_y2 = B_H

VARIANT_B = Variant(
    key="b",
    name="Thermally isolated",
    revision="HW B1",
    width=B_W, height=B_H, body_dx=0.0,
    outline=[
        (0, 0), (B_W, 0), (B_W, _y0),
        (_nx1, _y0), (_nx1, _y1),          # right side of the neck
        (_ix1, _y1), (_ix1, _y2),          # island right
        (_ix0, _y2), (_ix0, _y1),          # island left
        (_nx0, _y1), (_nx0, _y0),          # left side of the neck
        (0, _y0),
    ],
    sensor_xy=(B_W / 2.0, _y1 + 4.0),
    sensor_cap_xy=(B_W / 2.0 + 4.5, _y1 + 4.0),
    notes=("Same electronics block, then two routed slots leave a "
           f"{B_NECK_W} x {B_NECK_L} mm FR-4 neck. Four 0.15 mm traces cross "
           "it and nothing else - no plane, no pour, no stitching vias, no "
           "copper at all on In1/In2 across the neck."),
)

# Neck + island geometry exported for the rule zones and the enclosure model.
B_NECK_RECT = (_nx0, _y0 - 0.5, _nx1, _y1 + 0.5)
B_ISLAND_RECT = (_ix0, _y1, _ix1, _y2)

VARIANTS = {"a": VARIANT_A, "b": VARIANT_B}


def antenna_keepout(v: Variant) -> tuple[float, float, float, float]:
    """Mandatory no-copper / no-part rectangle around the module PCB antenna.

    Espressif ask for ~15 mm clear in every direction. Neither board is 30 mm
    wider than the module, so in-plane we give the antenna the **full width of
    the board** for its whole length and buy the rest of the clearance from the
    ENCLOSURE (requirement M-04). That costs ~170 mm2 of a ~1000 mm2 board and
    it is the right trade: RF range is a requirement, board area is not.

    The rectangle deliberately stops at the antenna boundary rather than
    extending into the module body - the module's own ground pads start 0.8 mm
    below it, and a keep-out that swallowed them would be self-contradictory.
    Recorded as EDS open item EDS-7.
    """
    cy = ANCHORED["U1"][1]
    # module local: body y -11.15..5.85, antenna is the top 5.4 mm of the body
    return (0.0, v.width, 0.0, cy - 5.6)


def sensor_keepout(v: Variant) -> tuple[float, float, float, float]:
    """No heat sources, no pour, no other parts near the sensor."""
    sx, sy = v.sensor_xy
    if v.key == "b":
        return B_ISLAND_RECT[0], B_ISLAND_RECT[2], B_ISLAND_RECT[1], B_ISLAND_RECT[3]
    return (sx - 5.0, sx + 5.0, sy - 3.0, v.height)
