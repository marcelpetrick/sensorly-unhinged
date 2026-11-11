# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from unittest.mock import patch
from tools.boardgen import plane_access
from tools.boardgen.place import place
from tools.boardgen.variants import VARIANTS


class PlaneAccessGuards(unittest.TestCase):
    def test_moved_pullup_requires_route_review(self):
        for variant in VARIANTS.values():
            placed = place(variant)
            next(p for p in placed if p.ref == 'R22').x += .1
            with self.subTest(variant=variant.key), self.assertRaisesRegex(ValueError, 'placement changed'):
                plane_access.route_plane_access(variant, placed)

    def test_changed_supply_assignment_is_rejected(self):
        placed = place(VARIANTS['a'])
        with patch.dict(plane_access.NETS, {'+3V0': [p for p in plane_access.NETS['+3V0']
                                                   if p != ('R22', '2')]}):
            with self.assertRaisesRegex(ValueError, 'no longer belongs'):
                plane_access.route_plane_access(VARIANTS['a'], placed)
