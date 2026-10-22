# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local charger power paths must reach actual transformed capacitor pads."""
import unittest
from collections import defaultdict,deque
from tools.boardgen import geometry as G
from tools.boardgen.place import place
from tools.boardgen.power import route_local_power
from tools.boardgen.variants import VARIANTS

class ChargerPowerTests(unittest.TestCase):
    def test_all_charger_power_pads_reach_their_local_bypass(self):
        for key,variant in VARIANTS.items():
            placed=place(variant);parts={p.ref:p for p in placed}
            tracks,_=route_local_power(variant,placed)
            def pad(ref,number):
                p=parts[ref];x,y=G.get(p.footprint).pads[number][0]
                return tuple(round(a,7) for a in G.xform(x,y,p.x,p.y,p.rot))
            for net,pin,cap in [('VBUS','13','C9'),('VSYS','10','C10'),('VSYS','11','C10'),('VBAT','2','C11'),('VBAT','3','C11')]:
                graph=defaultdict(set)
                selected=[t for t in tracks if t.net==net and t.layer=='F.Cu']
                points={tuple(round(x,7) for x in p) for t in selected for p in t.pts}
                for track in selected:
                    for a,b in zip(track.pts,track.pts[1:]):
                        # A pad escape may join the middle of a trunk segment.
                        split=sorted((p for p in points if G.distance_to_segment(p,a,b)<1e-7),
                                     key=lambda p:(p[0]-a[0])**2+(p[1]-a[1])**2)
                        for x,y in zip(split,split[1:]):
                            graph[x].add(y);graph[y].add(x)
                seen={pad('U4',pin)};pending=deque(seen)
                while pending:
                    for nxt in graph[pending.popleft()]-seen:
                        seen.add(nxt);pending.append(nxt)
                with self.subTest(variant=key,pin=pin,capacitor=cap):
                    self.assertIn(pad(cap,'1'),seen)
