# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-board supply bridges on In2; preserve the In1 ground reference.

These are geometry choices, not component specifications. Narrow QFN escapes
remain in power.py; the bridge joins their existing .4 mm VBAT trunk after the
outer-layer maze has finished, without rerouting a working signal branch.
"""
import math
from . import geometry as G
from .design import NETS
from .route import Track, Via


def route_remote_power(v, placed, tracks, vias):
    parts = {p.ref: p for p in placed}
    expected = {'C11': ('1', (23.05, 14.0)),
                'TP5': ('1', (19.16, 19.5)),
                'R14': ('1', (21.54,31.0) if v.key == 'a' else (19.04,29.75))}
    for ref, (pad, point) in expected.items():
        if (ref, pad) not in NETS['VBAT']:
            raise ValueError(f'{ref}.{pad} no longer belongs to VBAT')
        part = parts[ref]
        actual = G.xform(*G.get(part.footprint).pads[pad][0], part.x, part.y, part.rot)
        if math.dist(actual, point) > 1e-7:
            raise ValueError(f'{ref}.{pad} power-bridge placement changed')
    source = (22.2, 13.2)
    if not any(t.net == 'VBAT' and t.layer == 'F.Cu' and t.width >= .4 and
               any(G.distance_to_segment(source,a,b) < 1e-7 for a,b in zip(t.pts,t.pts[1:]))
               for t in tracks):
        raise ValueError('VBAT bridge source trunk changed')
    if not any(vv.net == 'VBAT' and math.dist((vv.x,vv.y),(19.2,20.0)) < 1e-7
               and abs(vv.size-.6)<1e-7 and abs(vv.drill-.3)<1e-7 for vv in vias):
        raise ValueError('VBAT bridge fixture via changed')
    out = [Track('VBAT', .4, 'In2.Cu',
                 [source,(23.4,14.4),(23.4,15.8),(21.8,15.8),(21.8,20.0),(19.2,20.0)])]
    out.append(Track('VBAT', .4, 'In2.Cu', [(21.8,20.0),(24.0,20.0)]))
    additions = [Via('VBAT',*source)]
    if v.key == 'a':
        pad, end = (21.54,31.0), (21.5,30.4)
        inner = [(24.0,20.0),(24.0,27.8),(21.5,27.8),end]
    else:
        pad, end = (19.04,29.75), (19.0,28.8)
        inner = [(24.0,20.0),(24.5,25.5),(24.5,27.6),(19.0,27.6),end]
    out += [Track('VBAT',.4,'F.Cu',[pad,end]), Track('VBAT',.4,'In2.Cu',inner)]
    additions.append(Via('VBAT',*end))
    G.validate_via_paste(placed, additions)
    return out, additions
