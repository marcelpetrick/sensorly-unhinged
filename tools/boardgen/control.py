# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reviewed low-current regulator controls in the common electronics frame.

Coordinates are engineering layout choices, not datasheet dimensions. Signal
via drills avoid paste lands and the input-capacitor ground-return region.
"""
from .route import Track, Via


def route_local_controls(placed):
    # Keep this snapshot beside the fixed paths: a configuration edit must not
    # silently leave a route connected to the previous component position.
    reviewed = {
        "U3": (3.4, 10.0, 270),
        "R5": (5.65, 9.5, 90),
        "R6": (5.9, 12.5, 90),
    }
    parts = {p.ref: p for p in placed}
    for ref, coords in reviewed.items():
        part = parts[ref]
        if any(abs(actual - expected) > 1e-7
               for actual, expected in zip((part.x, part.y, part.rot), coords)):
            raise ValueError(f"local control placement changed: {ref}; review its routes")
    tracks = [
        Track("EN_REG", .15, "F.Cu", [(2.65, 9.35), (2.65, 10), (2, 10)]),
        Track("EN_REG", .15, "F.Cu", [(5.65, 8.99), (5.65, 8.4)]),
        Track("EN_REG", .15, "B.Cu", [(2, 10), (5.65, 10), (5.65, 8.4)]),
        Track("VSET", .15, "F.Cu", [(2.65, 10.65), (1.9, 10.65), (1.9, 10.9)]),
        Track("VSET", .15, "F.Cu", [(5.9, 13.01), (5.9, 13.8)]),
        Track("VSET", .15, "B.Cu", [(1.9, 10.9), (1.4, 10.9), (1.4, 13.8), (5.9, 13.8)]),
    ]
    vias = [Via("EN_REG", 2, 10), Via("EN_REG", 5.65, 8.4),
            Via("VSET", 1.9, 10.9), Via("VSET", 5.9, 13.8)]
    return tracks, vias
