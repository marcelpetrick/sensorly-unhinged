# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from tools.boardgen.enclosure import build, check, planning_cell_fits, TOL, WALL
from tools.boardgen.variants import B_BODY_H, B_ISLAND_RECT, VARIANTS


class EnclosureTests(unittest.TestCase):
    def test_oversize_planning_cell_is_rejected(self):
        for v in VARIANTS.values():
            self.assertFalse(planning_cell_fits(build(v)))

    def test_divider_fits_only_over_narrow_neck(self):
        c = build(VARIANTS["b"])
        self.assertGreaterEqual(c.divider_y - WALL / 2, B_BODY_H + TOL)
        self.assertLessEqual(c.divider_y + WALL / 2, B_ISLAND_RECT[1] - TOL)

    def test_old_divider_position_is_rejected(self):
        c = build(VARIANTS["b"])
        c.divider_y = 33.5
        self.assertTrue(any("intersects" in p for p in check(VARIANTS["b"], c)))
