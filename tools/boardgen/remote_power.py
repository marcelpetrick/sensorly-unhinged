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


def route_system_power(v, placed, tracks, vias):
    """Join the shared C10/U4 output and C7/U3 input without altering In1."""
    parts = {p.ref: p for p in placed}
    for ref, pad, expected in (('C10','1',(28.2,11.45)), ('C7','1',(1.25,6.925))):
        if (ref,pad) not in NETS['VSYS']:
            raise ValueError(f'{ref}.{pad} no longer belongs to VSYS')
        part = parts[ref]
        point = G.xform(*G.get(part.footprint).pads[pad][0], part.x, part.y, part.rot)
        if math.dist(point,expected)>1e-7:
            raise ValueError(f'{ref}.{pad} system-power placement changed')
    for point in ((28.2,10.75),(2.0,6.9)):
        if not any(t.net=='VSYS' and t.layer=='F.Cu' and t.width>=.4 and
                   any(G.distance_to_segment(point,a,b)<=t.width/2
                       for a,b in zip(t.pts,t.pts[1:])) for t in tracks):
            raise ValueError('VSYS landing no longer sits on its reviewed trunk')
    additions=[Via('VSYS',29.2,10.5)]
    existing=[q for q in vias if math.dist((q.x,q.y),(2.0,6.9))<1e-7]
    if existing:
        if len(existing)!=1 or existing[0].net!='VSYS' or abs(existing[0].size-.6)>1e-7 or abs(existing[0].drill-.3)>1e-7:
            raise ValueError('VSYS input via changed')
    else:
        additions.append(Via('VSYS',2.0,6.9))
    # Shared geometry bends around the real through-via field, outside RF and
    # the guarded USB reference. It does not change any electrical value.
    path = [(29.2, 10.5), (25.7, 10.5), (25.7, 9.6), (25.6, 9.6), (25.6, 9.5), (25.5, 9.5), (25.5, 9.4), (25.4, 9.4), (25.4, 9.3), (25.3, 9.3), (25.3, 9.2), (23.3, 9.2), (23.3, 9.1), (23.2, 9.1), (23.2, 8.9), (23.1, 8.9), (23.1, 8.7), (22.9, 8.7), (22.9, 8.6), (22.7, 8.6), (22.7, 8.5), (19.6, 8.5), (19.6, 8.3), (19.5, 8.3), (19.5, 8.1), (19.3, 8.1), (19.3, 8.0), (19.1, 8.0), (19.1, 7.9), (6.2, 7.9), (6.2, 7.8), (6.1, 7.8), (6.1, 7.7), (5.8, 7.7), (5.8, 7.6), (2.0, 7.6), (2.0, 6.9)]
    routes=[Track('VSYS',.4,'F.Cu',[(28.2,10.75),(29.2,10.75),(29.2,10.5)]),
            Track('VSYS',.4,'In2.Cu',path)]
    if v.key == 'a':
        # B already joins these terminals through retained outer copper.
        for ref, pad, expected in (('R5','1',(5.65,10.01)), ('TP3','1',(14.08,19.5))):
            if (ref,pad) not in NETS['VSYS']:
                raise ValueError(f'{ref}.{pad} no longer belongs to VSYS')
            part=parts[ref]
            point=G.xform(*G.get(part.footprint).pads[pad][0],part.x,part.y,part.rot)
            if math.dist(point,expected)>1e-7:
                raise ValueError(f'{ref}.{pad} system-fixture placement changed')
        # The TP3 through drill is outside the 1.5mm pogo target copper.
        additions.extend((Via('VSYS',6.5,10.0),Via('VSYS',14.5,20.5)))
        routes.extend((
            Track('VSYS',.4,'F.Cu',[(5.65,10.01),(6.5,10.01),(6.5,10.0)]),
            Track('VSYS',.4,'B.Cu',[(14.08,19.5),(14.5,19.5),(14.5,20.5)]),
            Track('VSYS',.4,'In2.Cu',[[6.5, 10.0], [2.8, 10.0], [2.8, 9.8], [2.7, 9.8], [2.7, 9.6], [2.6, 9.6], [2.6, 9.4], [2.4, 9.4], [2.4, 9.3], [2.2, 9.3], [2.2, 9.2], [2.0, 9.2], [2.0, 6.9]]),
            Track('VSYS',.4,'In2.Cu',[[14.5, 20.5], [14.3, 20.5], [14.3, 20.4], [14.2, 20.4], [14.2, 20.2], [14.0, 20.2], [14.0, 20.1], [13.8, 20.1], [13.8, 20.0], [9.6, 20.0], [9.6, 19.9], [9.4, 19.9], [9.4, 19.8], [9.2, 19.8], [9.2, 18.7], [9.1, 18.7], [9.1, 18.5], [9.0, 18.5], [9.0, 18.3], [8.8, 18.3], [8.8, 18.2], [8.6, 18.2], [8.6, 18.1], [8.0, 18.1], [8.0, 15.3], [7.9, 15.3], [7.9, 15.1], [7.8, 15.1], [7.8, 14.9], [7.6, 14.9], [7.6, 12.9], [7.5, 12.9], [7.5, 12.7], [7.4, 12.7], [7.4, 12.5], [7.2, 12.5], [7.2, 12.4], [7.0, 12.4], [7.0, 12.3], [6.5, 12.3], [6.5, 10.0]]),
        ))
    G.validate_via_paste(placed,additions)
    return routes, additions
