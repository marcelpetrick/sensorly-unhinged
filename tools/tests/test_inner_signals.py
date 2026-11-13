# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Inner routing must retain physical holes, layer separation and USB reference."""
from dataclasses import replace
import re
import unittest
from unittest.mock import patch
from tools.boardgen import geometry as G
from tools.boardgen.autoroute import GRID
from tools.boardgen.design import NETS
from tools.boardgen.inner_signals import _inner_board, validate_mcu_supply_bridge, route_mcu_supply_bridge
from tools.boardgen.place import place
from tools.boardgen.route import Track, Via
from tools.boardgen.variants import VARIANTS


class InnerObstacleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.variant=VARIANTS['a']
        cls.placed=place(cls.variant)
        cls.pads={(r,p):n for n,pins in NETS.items() for r,p in pins}

    def board(self,tracks=()):
        return _inner_board(self.variant,self.placed,self.pads,'SDA',tracks,[])

    def test_usb_reference_and_every_connector_hole_are_occupied(self):
        board=self.board()
        self.assertFalse(board.free(100,240,0))
        part=next(p for p in self.placed if p.ref=='J1')
        for body in G._blocks(G.get(part.footprint).text,'pad '):
            if not re.match(r'\(pad "[^"]*" (?:np_)?thru_hole',body):continue
            at=re.search(r'\(at ([-\d.]+) ([-\d.]+)',body)
            x,y=G.xform(float(at[1]),float(at[2]),part.x,part.y,part.rot)
            with self.subTest(hole=(x,y)):
                self.assertFalse(board.free(round(x/GRID),round(y/GRID),0))

    def test_outer_smt_and_tracks_do_not_become_phantom_inner_obstacles(self):
        self.assertTrue(self.board().free(56,100,0))
        outer=Track('VBAT',.4,'F.Cu',[(20,10),(20,15)])
        inner=replace(outer,layer='In2.Cu')
        self.assertTrue(self.board([outer]).free(200,120,0))
        self.assertFalse(self.board([inner]).free(200,120,0))

    def test_missing_hole_geometry_fails_closed(self):
        part=next(p for p in self.placed if p.ref=='J1')
        original=G.get(part.footprint)
        body=next(b for b in G._blocks(original.text,'pad ') if 'np_thru_hole' in b)
        changed=replace(original,text=original.text.replace(body,re.sub(r'\(size [^)]+\)','',body,count=1),1))
        real_get=G.get
        with patch.object(G,'get',side_effect=lambda name: changed if name==part.footprint else real_get(name)):
            with self.assertRaisesRegex(ValueError,'cannot establish inner hole/pad occupancy'):
                self.board()

    def test_supply_bridge_requires_both_real_via_anchors(self):
        anchors=[Via('+3V0',7.4,9.1),Via('+3V0',6.7,6.4)]
        for bad in (anchors[:1], [Via('GND',7.4,9.1),anchors[1]],
                    [Via('+3V0',7.4,9.1,.8,.3),anchors[1]]):
            with self.subTest(vias=bad), self.assertRaisesRegex(ValueError,'supply bridge anchor changed'):
                validate_mcu_supply_bridge(self.variant,bad)

    def test_reserved_supply_bridge_tracks_real_endpoints(self):
        placed=place(self.variant)
        next(p for p in placed if p.ref=='C1').x += .1
        with self.assertRaisesRegex(ValueError,'supply bridge placement changed'):
            route_mcu_supply_bridge(self.variant,placed)
