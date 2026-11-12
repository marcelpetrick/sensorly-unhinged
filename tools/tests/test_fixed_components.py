# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixed copper joins only physically touching terminals and bridges layers at vias."""
import unittest

from tools.boardgen.autoroute import Board, _fixed_components, _terminals
from tools.boardgen.place import place
from tools.boardgen.route import Track, Via
from tools.boardgen.variants import VARIANTS


class FixedComponentTests(unittest.TestCase):
    def test_circular_bottom_test_pad_corner_is_not_copper(self):
        variant = VARIANTS['a']
        placed = place(variant)
        pad = next(t for t in _terminals(placed)['VBAT'] if t.ref == 'TP5')
        self.assertEqual(pad.layer, 1)
        x,y = pad.x,pad.y
        # Both objects reach the bounding square's upper-right corner, but
        # remain outside the actual 0.75 mm-radius circular copper land.
        corner_track = Track('VBAT', .15, 'B.Cu',
                             [(x+.68,y+.60),(x+.68,y+.70)])
        corner_via = Via('VBAT', x+.75,y+.75)
        groups = _fixed_components('VBAT',[pad],placed,[corner_track],
                                   [corner_via],Board(variant,placed))
        self.assertEqual(len(groups),2)
        self.assertEqual(next(g for g in groups if 0 in g['pads'])['pads'],{0})
        centre_track = Track('VBAT',.15,'B.Cu',[(x-.2,y),(x+.2,y)])
        centre_via = Via('VBAT',x,y)
        joined = _fixed_components('VBAT',[pad],placed,[centre_track],
                                   [centre_via],Board(variant,placed))
        self.assertEqual(len(joined),1)

    def test_roundrect_connector_mount_corner_is_not_copper(self):
        variant = VARIANTS['a']
        placed = place(variant)
        pad = next(t for t in _terminals(placed)['GND']
                   if t.ref == 'J2' and t.pad == 'MP')
        x,y = pad.x,pad.y
        # J2's 3.0 x 2.1 mm rotated roundrect has a 0.25 mm corner radius.
        # A 0.15 mm trace at its bounding corner still has a copper gap.
        corner = Track('GND',.15,'F.Cu',
                       [(x+1.5,y+1.05),(x+1.6,y+1.15)])
        separate = _fixed_components('GND',[pad],placed,[corner],[],
                                     Board(variant,placed))
        self.assertEqual(len(separate),2)
        centre = Track('GND',.15,'F.Cu',[(x,y),(x+.2,y)])
        joined = _fixed_components('GND',[pad],placed,[centre],[],
                                   Board(variant,placed))
        self.assertEqual(len(joined),1)

    def test_disconnected_island_and_real_via_bridge(self):
        variant = VARIANTS['a']
        placed = place(variant)
        terms = [next(t for t in _terminals(placed)['VBAT_SENSE']
                      if (t.ref, t.pad) == pair)
                 for pair in (('R14', '2'), ('R15', '1'), ('C13', '1'))]
        via = Via('VBAT_SENSE', 22.5, 30.5)
        tracks = [Track('VBAT_SENSE', .15, 'F.Cu',
                        [(terms[0].x, terms[0].y), (22.5, 31.0), (22.5, 30.5)]),
                  Track('VBAT_SENSE', .15, 'B.Cu',
                        [(22.5, 30.5), (23.0, 30.5)]),
                  Track('VBAT_SENSE', .15, 'F.Cu',
                        [(terms[1].x, terms[1].y), (23.7, 31.0)])]
        groups = _fixed_components('VBAT_SENSE', terms, placed, tracks,
                                   [via], Board(variant, placed))
        joined = next(g for g in groups if 0 in g['pads'])
        self.assertEqual(joined['pads'], {0})
        self.assertIn((225, 305, 0), joined['nodes'])
        self.assertIn((225, 305, 1), joined['nodes'])
        self.assertTrue(all(i not in joined['pads'] for i in (1, 2)))


if __name__ == '__main__':
    unittest.main()
