# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local charger paths must reach transformed component pads and ground vias."""
import unittest
from collections import defaultdict, deque
from tools.boardgen import geometry as G
from tools.boardgen.place import place
from tools.boardgen.power import route_local_power
from tools.boardgen.variants import VARIANTS


def component(tracks, net, start):
    graph = defaultdict(set)
    selected = [t for t in tracks if t.net == net and t.layer == 'F.Cu']
    points = {tuple(round(x, 7) for x in p) for t in selected for p in t.pts}
    for track in selected:
        for a, b in zip(track.pts, track.pts[1:]):
            # Include T junctions where an escape joins a trunk's middle.
            split = sorted((p for p in points if G.distance_to_segment(p, a, b) < 1e-7),
                           key=lambda p: (p[0]-a[0])**2+(p[1]-a[1])**2)
            for x, y in zip(split, split[1:]):
                graph[x].add(y)
                graph[y].add(x)
    seen = {start}
    pending = deque(seen)
    while pending:
        for nxt in graph[pending.popleft()]-seen:
            seen.add(nxt)
            pending.append(nxt)
    return seen


class ChargerPowerTests(unittest.TestCase):
    def test_charger_power_and_programming_paths_reach_actual_parts(self):
        for key, variant in VARIANTS.items():
            placed = place(variant)
            parts = {p.ref: p for p in placed}
            tracks, vias = route_local_power(variant, placed)
            def pad(ref, number):
                p = parts[ref]
                x, y = G.get(p.footprint).pads[number][0]
                return tuple(round(a, 7) for a in G.xform(x, y, p.x, p.y, p.rot))
            for net, pin, ref in [('VBUS','13','C9'), ('VSYS','10','C10'),
                                  ('VSYS','11','C10'), ('VBAT','2','C11'),
                                  ('VBAT','3','C11'), ('ISET','16','R13'),
                                  ('ITERM','15','R12')]:
                with self.subTest(variant=key, pin=pin, target=ref):
                    self.assertIn(pad(ref, '1'), component(tracks, net, pad('U4', pin)))
            for ref in ('R12', 'R13'):
                ground = component(tracks, 'GND', pad(ref, '2'))
                with self.subTest(variant=key, ground_return=ref):
                    self.assertTrue(any(v.net == 'GND' and (v.x, v.y) in ground for v in vias))

    def test_programming_component_move_requires_route_review(self):
        for variant in VARIANTS.values():
            for ref in ('R12', 'R13', 'C9'):
                placed = place(variant)
                next(p for p in placed if p.ref == ref).x += .1
                with self.subTest(variant=variant.key, ref=ref):
                    with self.assertRaisesRegex(ValueError, ref):
                        route_local_power(variant, placed)
