# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Complete EN fixture branches against physically connected retained copper.

The search is additive: final retained copper and all foreign obstacles remain
occupied. No placement, width, clearance or thermal/RF exclusion is relaxed.
"""
import math
from . import geometry as G


def _check_endpoints(placed):
    from .design import NETS
    expected = {('U1', '8'): (8.1, 13.1), ('TP6', '1'): (21.7, 19.5),
                ('R1', '2'): (6.26, 18.0), ('C4', '1'): (23.5, 16.98)}
    parts = {p.ref: p for p in placed}
    for pair, point in expected.items():
        if pair not in NETS['EN']:
            raise ValueError(f'{pair[0]}.{pair[1]} no longer belongs to EN')
        part = parts[pair[0]]
        actual = G.xform(*G.get(part.footprint).pads[pair[1]][0], part.x, part.y, part.rot)
        if math.dist(actual, point) > 1e-7:
            raise ValueError(f'{pair[0]}.{pair[1]} EN placement changed; review fixture branch')


def route_fixture_branches(v, placed, tracks, vias):
    _check_endpoints(placed)
    from .autoroute import (Board, _fixed_components, _terminals, _search,
                            _to_geometry, exact_via_mask, SIGNAL_W, GRID)
    from .design import NETS
    pads = {(r,p):n for n, conns in NETS.items() for r,p in conns}
    terminals = _terminals(placed)
    extra_tracks, extra_vias = [], []
    for net in ('EN',):
        for attempt in range(len(terminals[net])-1):
            all_tracks = tracks + extra_tracks
            all_vias = vias + extra_vias
            board = Board(v, placed)
            board.add_pads(net, pads, SIGNAL_W)
            for tr in all_tracks:
                if tr.net != net: board.add_track(tr, SIGNAL_W, net)
            for via in all_vias:
                if via.net != net: board.add_via(via, SIGNAL_W, net)
            groups = [g for g in _fixed_components(net, terminals[net], placed,
                      all_tracks, all_vias, board) if g['pads']]
            if len(groups)<2: break
            groups.sort(key=lambda g:len(g['nodes']))
            mask = exact_via_mask(v,placed,pads,net,all_tracks,all_vias)
            found = False
            for target in groups:
                sources = set().union(*(g['nodes'] for g in groups if g is not target))
                sources = {node for node in sources if all(
                    (node[0],node[1])==(round(via.x/GRID),round(via.y/GRID))
                    or math.hypot(node[0]*GRID-via.x,node[1]*GRID-via.y)>(via.size+SIGNAL_W)/2
                    for via in all_vias if via.net==net)}
                path = _search(board,sources,target['nodes'],True,mask)
                if path is None: continue
                ts, vs = _to_geometry(path,SIGNAL_W,net)
                if any(math.hypot(a.x-b.x,a.y-b.y)<.9 for i,a in enumerate(vs) for b in vs[i+1:]): continue
                G.validate_via_paste(placed,vs)
                extra_tracks+=ts;extra_vias+=vs;found=True
                print(f'      fixture completion: {v.key} {net}, {len(ts)} tracks / {len(vs)} vias', flush=True)
                break
            if not found: break
    return extra_tracks,extra_vias
