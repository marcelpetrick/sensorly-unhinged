# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Same-net copper permission must not authorize an open hole under paste."""
import unittest
from tools.boardgen import geometry as G
from tools.boardgen.autoroute import GRID, exact_via_mask
from tools.boardgen.design import NETS
from tools.boardgen.pcb import emit
from tools.boardgen.place import place
from tools.boardgen.route import Track, Via
from tools.boardgen.variants import VARIANTS


class ViaPasteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.variant = VARIANTS['a']
        cls.parts = {p.ref: p for p in place(cls.variant)}

    def test_export_rejects_same_net_drill_in_capacitor_paste(self):
        part = self.parts['C9']
        x, y = G.xform(*G.get(part.footprint).pads['2'][0], part.x, part.y, part.rot)
        with self.assertRaisesRegex(ValueError, 'C9.2 paste'):
            emit(self.variant, [part], [], [Via('GND', x, y)])

    def test_outside_paste_return_is_accepted(self):
        G.validate_via_paste([self.parts['C9']], [Via('GND', 22.4, 6.4)])

    def test_reviewed_ep_array_is_the_only_process_exception(self):
        part = self.parts['U4']
        vias = [Via('GND', part.x+dx, part.y+dy) for dx in (-.55,.55) for dy in (-.55,.55)]
        G.validate_via_paste([part], vias)
        vias[0].x += .05
        with self.assertRaisesRegex(ValueError, 'U4.17 paste'):
            G.validate_via_paste([part], vias)

    def test_ep_exception_does_not_apply_to_other_nets(self):
        part = self.parts['U4']
        with self.assertRaisesRegex(ValueError, 'U4.17 paste'):
            G.validate_via_paste([part], [Via('VBAT', part.x+.55, part.y+.55)])

    def test_generic_router_cannot_put_same_net_drill_under_paste(self):
        part = self.parts['C9']
        padnet = {(ref,pad):net for net,pins in NETS.items() for ref,pad in pins}
        mask = exact_via_mask(self.variant, [part], padnet, 'GND', [], [])
        from tools.boardgen.autoroute import Board
        board = Board(self.variant, [part])
        def blocked(x,y):
            return mask[round(y/GRID)*board.w+round(x/GRID)]
        x,y = G.xform(*G.get(part.footprint).pads['2'][0],part.x,part.y,part.rot)
        self.assertTrue(blocked(x,y))
        self.assertFalse(blocked(22.4,6.4))

    def test_same_net_corner_requires_centred_via(self):
        from tools.boardgen.autoroute import Board
        board = Board(self.variant, [])
        track = Track('TEST', .15, 'F.Cu', [(10,10),(13,10)])
        mask = exact_via_mask(self.variant, [], {}, 'TEST', [track], [])
        def blocked(x,y):
            return mask[round(y/GRID)*board.w+round(x/GRID)]
        self.assertFalse(blocked(10,10))
        self.assertTrue(blocked(10,10.3))
        self.assertFalse(blocked(10,10.5))
        occupied = exact_via_mask(self.variant, [], {}, 'TEST', [track],
                                  [Via('OTHER',10,10)])
        self.assertTrue(occupied[round(10/GRID)*board.w+round(10/GRID)])
