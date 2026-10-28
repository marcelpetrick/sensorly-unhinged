# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pad-derived ground returns for body regions that a perimeter grid misses.

Offsets and the 0.10 mm drill-to-paste reserve are explicit layout assumptions.
Filled-board DRC still checks real copper/holes and plane connectivity.
"""
from . import geometry as G
from .design import NETS
from .route import Track, Via
from .variants import B_NECK_RECT, antenna_keepout, sensor_keepout


def route_ground_returns(variant, placed):
    by_ref = {p.ref: p for p in placed}
    # Local pad-frame offsets: avoid the USB main-path corridor beneath U1.14.
    anchors = [("U1", "11", (-.9, 0)), ("U1", "14", (0, -1.1)),
               ("U1", "51", (.95, 0)), ("U1", "52", (-.85, 0)),
               ("J2", "1", (0, -1.3)),
               ("C5", "2", (.8, 0))]
    # U5/C14 returns belong to the dedicated USB module. Its public-emitter
    # guard checks actual pad-to-ground-via connectivity independently.
    ax0, ax1, ay0, ay1 = antenna_keepout(variant)
    sx0, sx1, sy0, sy1 = sensor_keepout(variant)
    protected = [(ax0, ax1, ay0, ay1), (sx0, sx1, sy0, sy1)]
    if variant.key == 'b':
        x0, y0, x1, y1 = B_NECK_RECT
        protected.append((x0, x1, y0, y1))
    tracks, vias = [], []
    for ref, number, (dx, dy) in anchors:
        if (ref, number) not in NETS["GND"]:
            raise ValueError(f"{ref}.{number} is no longer a GND anchor")
        part = by_ref[ref]
        fp = G.get(part.footprint)
        if fp.bottom:
            raise ValueError(f'{ref} ground return requires its reviewed top-side footprint')
        lx, ly = fp.pads[number][0]
        start = G.xform(lx, ly, part.x, part.y, part.rot)
        x, y = G.xform(lx+dx, ly+dy, part.x, part.y, part.rot)
        x, y = round(x, 4), round(y, 4)
        box = (x-.3, x+.3, y-.3, y+.3)
        if not G.box_inside_polys(box, variant.polys, margin=.3) or any(
                G.boxes_overlap(box, area) for area in protected):
            raise ValueError(f'{ref}.{number} ground via enters a protected/edge region')
        path_box = (min(start[0], x)-.2, max(start[0], x)+.2,
                    min(start[1], y)-.2, max(start[1], y)+.2)
        if not G.box_inside_polys(path_box, variant.polys, margin=.3) or any(
                G.boxes_overlap(path_box, area) for area in protected):
            raise ValueError(f'{ref}.{number} ground path enters a protected/edge region')
        points = [start, (x, y)]
        tracks.append(Track('GND', .4, 'F.Cu', points))
        vias.append(Via('GND', x, y))
    G.validate_via_paste(placed, vias)
    return tracks, vias
