# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Occupancy-aware signal bridges on In2; preserve In1 and the USB reference."""
import math
from . import geometry as G


def route_mcu_supply_bridge(v, placed):
    """Reserve the reviewed A supply jumper before any generic routing."""
    if v.key != 'a': return []
    from .design import NETS
    from .route import Track
    parts={p.ref:p for p in placed}
    for ref,pad,expected in (('U1','3',(8.1,9.1)),('C1','1',(5.85,7.1))):
        if (ref,pad) not in NETS['+3V0']:
            raise ValueError('MCU supply bridge endpoint net changed')
        part=parts[ref];fp=G.get(part.footprint)
        point=G.xform(*fp.pads[pad][0],part.x,part.y,part.rot)
        if fp.bottom or math.dist(point,expected)>1e-7:
            raise ValueError('MCU supply bridge placement changed')
    return [Track('+3V0',.4,'B.Cu',[(7.4,9.1),(7.4,6.4),(6.7,6.4)])]


def validate_mcu_supply_bridge(v, vias):
    """Require real through-via anchors after the plane-feed stage."""
    if v.key != 'a': return
    for point in ((7.4,9.1),(6.7,6.4)):
        anchors=[q for q in vias if math.dist((q.x,q.y),point)<1e-7]
        if len(anchors)!=1 or anchors[0].net!='+3V0' or abs(anchors[0].size-.6)>1e-7 or abs(anchors[0].drill-.3)>1e-7:
            raise ValueError('MCU supply bridge anchor changed; review plane connectivity')


def _inner_board(v, placed, pads, net, tracks, vias):
    """Conservative In2 occupancy; outer SMT copper does not occupy this layer."""
    from dataclasses import replace
    from .autoroute import Board, SIGNAL_W
    inner_board = Board(v, placed)
    # Keep the existing In2 GND reference under the bottom USB pair intact.
    from .usbroute import REFERENCE_RECT
    x0, y0, x1, y1 = REFERENCE_RECT
    margin = SIGNAL_W/2 + .06
    inner_board.block(0, x0-margin, y0-margin, x1+margin, y1+margin)
    # PTH/NPTH copper and holes occupy inner layers too; SMT pads do not.
    import re
    for part in placed:
        fp = G.get(part.footprint)
        for body in G._blocks(fp.text, 'pad '):
            match = re.match(r'\(pad "([^\"]*)" (\w+)', body)
            if not match or match[2] not in ('thru_hole', 'np_thru_hole'):
                continue
            if pads.get((part.ref, match[1])) == net:
                continue
            at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', body)
            size = re.search(r'\(size ([-\d.]+) ([-\d.]+)\)', body)
            if not at or not size:
                raise ValueError('cannot establish inner hole/pad occupancy')
            angle=math.radians(float(at[3] or 0))
            corners=[]
            for dx in (-float(size[1])/2,float(size[1])/2):
                for dy in (-float(size[2])/2,float(size[2])/2):
                    x=float(at[1])+dx*math.cos(angle)-dy*math.sin(angle)
                    y=float(at[2])+dx*math.sin(angle)+dy*math.cos(angle)
                    corners.append(G.xform(x,y,part.x,part.y,part.rot))
            # .45mm is a conservative search envelope, not a relaxed DRC limit.
            inner_board.block(0,min(x for x,y in corners)-.45,min(y for x,y in corners)-.45,
                              max(x for x,y in corners)+.45,max(y for x,y in corners)+.45)
    for via in vias:
        if via.net != net: inner_board.add_via(via, SIGNAL_W, net)
    for tr in tracks:
        if tr.layer == 'In2.Cu' and tr.net != net:
            inner_board.add_track(replace(tr, layer='F.Cu'), SIGNAL_W, net)
    return inner_board


def route_inner_signals(v, placed, tracks, vias):
    from dataclasses import replace
    from .autoroute import (Board, _fixed_components, _terminals, _search,
                            _to_geometry, _via_spots, exact_via_mask, SIGNAL_W,
                            GRID, VIA_SIZE)
    from .design import NETS
    from .route import Track, Via
    pads = {(r,p):n for n, conns in NETS.items() for r,p in conns}
    terminals = _terminals(placed)
    extra_t, extra_v = [], []
    selected = ('SDA', 'PACK_TS_SENSE', 'VBAT_SENSE', 'CHG_N')
    for net in selected:
        outer = [t for t in tracks + extra_t if t.layer in ('F.Cu','B.Cu')]
        all_vias = vias + extra_v
        outer_board = Board(v, placed)
        outer_board.add_pads(net, pads, SIGNAL_W)
        for tr in outer:
            if tr.net != net: outer_board.add_track(tr, SIGNAL_W, net)
        for via in all_vias:
            if via.net != net: outer_board.add_via(via, SIGNAL_W, net)
        groups = [g for g in _fixed_components(net, terminals[net], placed,
                  outer, all_vias, outer_board) if g['pads']]
        if len(groups)<2: continue
        inner_board = _inner_board(v, placed, pads, net, tracks + extra_t, all_vias)
        mask = exact_via_mask(v, placed, pads, net, outer, all_vias)
        via_board = Board(v, placed)
        for tr in tracks + extra_t:
            if tr.layer == 'In2.Cu' and tr.net != net:
                via_board.add_track(replace(tr, layer='F.Cu'), VIA_SIZE, net)
        mask = bytearray(a or b for a,b in zip(mask,via_board.blocked[0]))
        outlets = []
        for group in groups:
            options=[]
            for via in all_vias:
                cell=(round(via.x/GRID),round(via.y/GRID),0)
                if via.net==net and cell in group['nodes'] and inner_board.free(*cell):
                    options.append((cell,[],[]))
            if not options:
                sources = group['nodes']
                for i in sorted(group['pads']):
                    term=terminals[net][i]
                    for x,y in _via_spots(outer_board,term,mask,limit=128):
                        if not inner_board.free(x,y,0): continue
                        target=(x,y,term.layer)
                        path=_search(outer_board,sources,{target},False,max_steps=25)
                        if path is None: continue
                        ts,_unused = _to_geometry(path,SIGNAL_W,net)
                        via=Via(net,round(x*GRID,3),round(y*GRID,3))
                        try: G.validate_via_paste(placed,[via])
                        except ValueError: continue
                        options.append(((x,y,0),ts,[via]))
                        if len(options)>=6: break
                    if len(options)>=6: break
            outlets.append(options)
        connected=None
        for i, options in enumerate(outlets):
            if options:
                connected=i; break
        if connected is None: continue
        anchor=outlets[connected]
        for j,target_options in enumerate(outlets):
            if j==connected or not target_options: continue
            found=False
            for start, st, sv in anchor:
                for end, et, ev in target_options:
                    path=_search(inner_board,{start},{end},False)
                    if path is None: continue
                    inner, _unused = _to_geometry(path,SIGNAL_W,net)
                    inner = [replace(tr,layer='In2.Cu') for tr in inner]
                    extra_t += st + et + inner
                    extra_v += sv + ev
                    print('      inner fixture:',v.key,net,[(t.layer,t.pts) for t in st+et+inner],[(q.x,q.y) for q in sv+ev],flush=True)
                    # Additional groups reuse the actual connected root via.
                    anchor=[(start,[],[])]
                    found=True;break
                if found: break
    validate_mcu_supply_bridge(v, vias + extra_v)
    return extra_t, extra_v
