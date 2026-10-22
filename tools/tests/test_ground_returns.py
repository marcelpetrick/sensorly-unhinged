# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ground paths must follow real net anchors and obey shared process guards."""
import unittest
from unittest.mock import patch

from tools.boardgen import geometry as G
from tools.boardgen.design import NETS
from tools.boardgen.ground import route_ground_returns
from tools.boardgen.place import place
from tools.boardgen.variants import VARIANTS


class GroundReturnTests(unittest.TestCase):
    def test_moving_capacitor_moves_return_and_preserves_paste_reserve(self):
        for variant in VARIANTS.values():
            placed = place(variant)
            before, _ = route_ground_returns(variant, placed)
            next(p for p in placed if p.ref == 'C5').x += .1
            after, vias = route_ground_returns(variant, placed)
            self.assertAlmostEqual(after[-1].pts[0][0]-before[-1].pts[0][0], .1)
            self.assertAlmostEqual(after[-1].pts[1][0]-before[-1].pts[1][0], .1)
            G.validate_via_paste(placed, vias)

    def test_changed_anchor_net_is_rejected(self):
        changed = [anchor for anchor in NETS['GND'] if anchor != ('U1', '14')]
        with patch.dict(NETS, {'GND': changed}):
            with self.assertRaisesRegex(ValueError, 'no longer a GND anchor'):
                route_ground_returns(VARIANTS['a'], place(VARIANTS['a']))

    def test_usb_placement_change_requires_dedicated_ground_return(self):
        variant = VARIANTS['a']
        placed = place(variant)
        next(p for p in placed if p.ref == 'U5').rot = 90
        with self.assertRaisesRegex(ValueError, 'dedicated USB return'):
            route_ground_returns(variant, placed)

    def test_component_move_into_sensor_region_is_rejected(self):
        variant = VARIANTS['b']
        placed = place(variant)
        next(p for p in placed if p.ref == 'C5').y = 46
        with self.assertRaisesRegex(ValueError, 'protected/edge region'):
            route_ground_returns(variant, placed)
