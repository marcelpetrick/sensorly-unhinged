# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reviewed local power loops, before the generic router occupies their space.

Coordinates are mm in the common electronics frame. They are routing geometry,
not datasheet values. U3/L1 orientation and bypass placements live in variants.
"""
import math
from .route import Track, Via
from . import geometry as G


def route_local_power(v, placed):
    # This literal snapshot belongs to the reviewed routing waypoints below.
    # Compare actual placement, not its live configuration against itself:
    # changing the common placement table must trigger a route review.
    reviewed = {
        'U3':(3.4,10.0,270),'L1':(3.4,13.2,180),'U4':(24.4,10.5,0),
        'C1':(4.9,7.1,180),'C7':(1.25,7.7,270),'C8':(2.8,15.8,180),
        'C9':(24.4,7.1,0),'C10':(28.2,10.5,90),'C11':(24.0,14.0,0),
        'Q1':(27.8,17.1,90),
    }
    by_ref = {p.ref:p for p in placed}
    for ref, coords in reviewed.items():
        p = by_ref[ref]
        if any(abs(a-b)>1e-7 for a,b in zip((p.x,p.y,p.rot),coords)):
            raise ValueError(f'local power placement changed: {ref}; review its routes')
    tracks = [
        Track('SW_L', .15, 'F.Cu', [(3.65,10.65),(3.65,11.8)], 'switch-neckdown'),
        Track('SW_L', .6, 'F.Cu', [(3.65,11.8),(3.65,11.85),(4.2,11.85),(4.2,13.2)]),
        Track('+3V0', .15, 'F.Cu', [(4.15,10.65),(4.15,10.9),(5.1,10.9)], 'power-neckdown'),
        Track('+3V0', .4, 'F.Cu', [(5.1,10.9),(5.1,15.8),(3.75,15.8)]),
        Track('+3V0', .4, 'F.Cu', [(2.6,13.2),(2.6,14.5),(3.75,14.5),(3.75,15.8)]),
        Track('VSYS', .15, 'F.Cu', [(3.65,9.35),(3.65,8.5),(3.65,8.3)], 'power-neckdown'),
        Track('VSYS', .4, 'F.Cu', [(3.65,8.3),(2.95,8.3),(2.95,6.925),(1.25,6.925)]),
        Track('GND', .15, 'F.Cu', [(3.15,9.35),(3.15,10.65)], 'plane-neckdown'),
        Track('GND', .15, 'F.Cu', [(4.15,9.35),(4.15,8.8),(4.65,8.5)], 'plane-neckdown'),
        Track('GND', .15, 'F.Cu', [(3.15,10.65),(3.15,11.35),(2.3,11.6)], 'plane-neckdown'),
        # Direct VSS8-to-EP link required by SLUS810N section12.3.
        Track('GND', .15, 'F.Cu', [(25.15,11.9),(25.15,11.4),(24.95,11.05)], 'plane-neckdown'),
        Track('GND', .4, 'F.Cu', [(1.25,8.475),(1.0,8.475),(1.0,9.4)]),
        Track('GND', .4, 'F.Cu', [(1.85,15.8),(1.0,15.8)]),
        Track('GND', .4, 'F.Cu', [(25.35,7.1),(26.4,7.1),(26.4,6.4)]),
        Track('GND', .4, 'F.Cu', [(28.2,9.55),(29.25,9.55)]),
        Track('GND', .4, 'F.Cu', [(24.95,14.0),(24.95,15.1)]),
    ]
    # U4 bypass loops: each .5mm-pitch power pad escapes narrowly, then
    # immediately joins .4mm trunks and its local capacitor on F.Cu.
    tracks += [
        Track('VBUS',.15,'F.Cu',[(25.15,9.1),(25.15,8.3)],'power-neckdown'),
        Track('VBUS',.4,'F.Cu',[(25.15,8.3),(23.45,8.3),(23.45,7.1)]),
        Track('VSYS',.15,'F.Cu',[(25.8,10.25),(26.6,10.25)],'power-neckdown'),
        Track('VSYS',.15,'F.Cu',[(25.8,10.75),(26.6,10.75)],'power-neckdown'),
        Track('VSYS',.4,'F.Cu',[(26.6,10.25),(26.6,10.75),(28.2,10.75),(28.2,11.45)]),
        Track('VBAT',.15,'F.Cu',[(23.0,10.25),(22.2,10.25)],'power-neckdown'),
        Track('VBAT',.15,'F.Cu',[(23.0,10.75),(22.2,10.75)],'power-neckdown'),
        Track('VBAT',.4,'F.Cu',[(22.2,10.25),(22.2,13.2),(23.05,13.2),(23.05,14.0)]),
    ]
    vias = [Via('GND',4.65,8.5), Via('GND',2.3,11.6),
            Via('+3V0',5.1,15.8), Via('GND',1.0,9.4), Via('GND',1.0,15.8),
            Via('GND',26.4,6.4), Via('GND',29.25,9.55), Via('GND',24.95,15.1)]
    # Exact TI RGT0016B example (4219033/A08/2016) centres +/-0.55.
    # .6/.3 is the project's standard via, NOT TI's illustrated .2 bore.
    # Under-paste vias require explicitly approved filled/capped/planarized
    # process. Generic tent flags do not prove sealed holes under open EP mask.
    u4 = next(p for p in placed if p.ref == 'U4')
    vias += [Via('GND', u4.x+dx, u4.y+dy) for dx in (-.55,.55) for dy in (-.55,.55)]
    # Centre module ground-array vias between the primary land-pattern tiles;
    # holes stay outside paste apertures. Derive gap centres from vendored DXF.
    u1 = next(p for p in placed if p.ref == 'U1')
    fp = G.get(u1.footprint)
    xs = sorted({x for x,y in fp.pads['49']})
    ys = sorted({y for x,y in fp.pads['49']})
    for a,b in zip(xs,xs[1:]):
        for c,d in zip(ys,ys[1:]):
            x,y = G.xform((a+b)/2,(c+d)/2,u1.x,u1.y,u1.rot)
            vias.append(Via('GND',x,y))
    if v.body_dx:
        # All current electronics frames have dx=0; reject accidental partial
        # translation until local geometry becomes pad-relative throughout.
        raise ValueError('local power geometry requires the common dx=0 body frame')
    return tracks, vias


def validate_switch_routes(placed, tracks, vias):
    """One bounded pin7 escape; the complete switching path stays on F.Cu."""
    switch = [t for t in tracks if t.net == 'SW_L']
    if any(t.layer != 'F.Cu' for t in switch) or any(v.net == 'SW_L' for v in vias):
        raise ValueError('SW_L must stay on F.Cu without vias')
    thin = [t for t in switch if t.width < .6]
    if len(thin) > 1:
        raise ValueError('SW_L permits only one pin7 neckdown')
    if not thin:
        return
    track = thin[0]
    length = sum(math.hypot(bx-ax,by-ay) for (ax,ay),(bx,by) in zip(track.pts,track.pts[1:]))
    if track.width < .15 or track.purpose != 'switch-neckdown' or length > 1.2 + 1e-9:
        raise ValueError('invalid bounded Switch escape')
    u3 = next(p for p in placed if p.ref == 'U3')
    lx,ly = G.get(u3.footprint).pads['7'][0]
    pad = G.xform(lx,ly,u3.x,u3.y,u3.rot)
    if math.dist(track.pts[0],pad) <= 1e-7:
        end = track.pts[-1]
    elif math.dist(track.pts[-1],pad) <= 1e-7:
        end = track.pts[0]
    else:
        raise ValueError('Switch neckdown must start on U3.7')
    if not any(t.width >= .6 and any(G.distance_to_segment(end,a,b) <= 1e-7
            for a,b in zip(t.pts,t.pts[1:])) for t in switch):
        raise ValueError('Switch neckdown must terminate on its .6mm trunk')
