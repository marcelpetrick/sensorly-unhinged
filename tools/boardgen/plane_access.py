# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Off-paste main-board supply-plane returns for constrained pull-ups."""
from . import geometry as G
from .design import NETS
from .route import Track, Via


def route_plane_access(v, placed):
    by_ref = {p.ref: p for p in placed}
    tracks, vias = [], []
    for ref, number, expected, end in (
        ('R22', '2', (1.0, 11.89), (0.8, 11.2)),
    ):
        if (ref, number) not in NETS['+3V0']:
            raise ValueError(f'{ref}.{number} no longer belongs to +3V0')
        p = by_ref[ref]
        fp = G.get(p.footprint)
        point = G.xform(*fp.pads[number][0], p.x, p.y, p.rot)
        if fp.bottom or any(abs(a-b) > 1e-7 for a,b in zip(point, expected)):
            raise ValueError(f'{ref}.{number} supply-plane placement changed')
        tracks.append(Track('+3V0', .15, 'F.Cu', [point, (end[0], point[1]), end], 'plane-neckdown'))
        vias.append(Via('+3V0', *end))
    G.validate_via_paste(placed, vias)
    return tracks, vias
