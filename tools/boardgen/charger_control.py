# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reviewed U4 fine-pitch charger signal escapes in the common frame."""
from . import geometry as G
from .design import NETS
from .route import Track, Via


def route_charger_controls(v, placed):
    parts = {part.ref: part for part in placed}
    if (parts["U4"].x, parts["U4"].y, parts["U4"].rot) != (24.4, 10.5, 0):
        raise ValueError("U4 charger placement changed; review signal escapes")
    if ("U4", "1") not in NETS["PACK_TS"]:
        raise ValueError("U4.1 must remain PACK_TS")
    pad = G.xform(*G.get(parts["U4"].footprint).pads["1"][0],
                  parts["U4"].x, parts["U4"].y, parts["U4"].rot)
    if tuple(round(v, 3) for v in pad) != (23.0, 9.75):
        raise ValueError("U4.1 land-pattern position changed")
    if v.key == "a":
        # The compact board leaves the two non-U4 CHARGE_EN_N terminals
        # separated by the crowded Q1/LED region. Retain the verified U4
        # escape for a later placement/routing pass and join Q1 to R18 here.
        for ref, number, net, expected in (
                ("Q1", "3", "CHARGE_EN_N", (27.8, 16.125)),
                ("R18", "1", "CHARGE_EN_N", (18.64, 28.0)),
                ("Q1", "1", "CHARGE_ENABLE", (26.85, 18.075)),
                ("R7", "1", "CHARGE_ENABLE", (27.65, 7.76))):
            if (ref, number) not in NETS[net]:
                raise ValueError(f"{ref}.{number} must remain {net}")
            part = parts[ref]
            actual = G.xform(*G.get(part.footprint).pads[number][0],
                             part.x, part.y, part.rot)
            if any(abs(a - e) > 1e-7 for a, e in zip(actual, expected)):
                raise ValueError(f"{ref}.{number} {net} position changed")
        tracks = [
            Track("CHARGE_EN_N", .15, "F.Cu",
                  [(27.8, 16.1), (26.2, 16.1), (26.2, 17.8), (23.2, 17.8)]),
            Track("CHARGE_EN_N", .15, "B.Cu", [(23.2, 17.8), (23.2, 28.7)]),
            Track("CHARGE_EN_N", .15, "F.Cu",
                  [(23.2, 28.7), (18.6, 28.7), (18.6, 28.0)]),
            Track("CHARGE_ENABLE", .15, "F.Cu",
                  [(26.8, 18.1), (27.6, 18.1)]),
            Track("CHARGE_ENABLE", .15, "B.Cu",
                  [(27.6, 18.1), (27.6, 8.3)]),
            Track("CHARGE_ENABLE", .15, "F.Cu",
                  [(27.6, 8.3), (27.6, 7.8)]),
        ]
        vias = [Via("CHARGE_EN_N", 23.2, 17.8),
                Via("CHARGE_EN_N", 23.2, 28.7),
                Via("CHARGE_ENABLE", 27.6, 18.1),
                Via("CHARGE_ENABLE", 27.6, 8.3)]
        G.validate_via_paste(placed, vias)
        return tracks, vias
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
