# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reviewed U4 fine-pitch charger signal escapes in the common frame."""
from . import geometry as G
from .design import NETS
from .route import Track, Via


def route_charger_controls(v, placed):
    if v.key != "b":
        return [], []  # A's existing CHG_N trunk occupies this TS via site.
    parts = {part.ref: part for part in placed}
    if (parts["U4"].x, parts["U4"].y, parts["U4"].rot) != (24.4, 10.5, 0):
        raise ValueError("U4 charger placement changed; review signal escapes")
    if ("U4", "1") not in NETS["PACK_TS"]:
        raise ValueError("U4.1 must remain PACK_TS")
    pad = G.xform(*G.get(parts["U4"].footprint).pads["1"][0],
                  parts["U4"].x, parts["U4"].y, parts["U4"].rot)
    if tuple(round(v, 3) for v in pad) != (23.0, 9.75):
        raise ValueError("U4.1 land-pattern position changed")
    via = Via("PACK_TS", 22.5, 9.3)
    tracks = [Track("PACK_TS", .15, "F.Cu",
                    [pad, (22.5, 9.75), (via.x, via.y)])]
    vias = [via]
    if v.key == "b":
        if ("J2", "2") not in NETS["PACK_TS"]:
            raise ValueError("J2.2 must remain PACK_TS")
        j2 = parts["J2"]
        j2_pad = G.xform(*G.get(j2.footprint).pads["2"][0],
                         j2.x, j2.y, j2.rot)
        if tuple(round(c, 3) for c in j2_pad) != (22.4, 24.5):
            raise ValueError("J2.2 PACK_TS position changed")
        tracks.extend((
            Track("PACK_TS", .15, "B.Cu",
                  [(22.5, 9.3), (26.5, 9.3), (26.5, 24.5), (23.5, 24.5)]),
            Track("PACK_TS", .15, "F.Cu", [(23.5, 24.5), j2_pad]),
        ))
        vias.append(Via("PACK_TS", 23.5, 24.5))
    G.validate_via_paste(placed, vias)
    return tracks, vias
