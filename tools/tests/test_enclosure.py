# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from tools.boardgen.enclosure import (
    BATT_Z, BATT_Z_ALLOW, SUPPORT_H, build, check, planning_cell_fits,
    HEIGHTS, TOL, WALL,
)
from tools.boardgen.variants import B_BODY_H, B_ISLAND_RECT, VARIANTS


class EnclosureTests(unittest.TestCase):
    def test_usb_opening_covers_the_connector_above_the_board(self):
        for v in VARIANTS.values():
            cut = next(c for c in build(v).cutouts if c.ref == "J1")
            self.assertLessEqual(cut.z - cut.height/2, 0)
            self.assertGreaterEqual(cut.z + cut.height/2, HEIGHTS["J1"][0])

    def test_selected_pack_fits_both_variants(self):
        for v in VARIANTS.values():
            c = build(v)
            self.assertTrue(planning_cell_fits(c))
            self.assertGreaterEqual(c.board_z - SUPPORT_H - BATT_Z, BATT_Z_ALLOW)

    def test_divider_fits_only_over_narrow_neck(self):
        c = build(VARIANTS["b"])
        self.assertGreaterEqual(c.divider_y - WALL / 2, B_BODY_H + TOL)
        self.assertLessEqual(c.divider_y + WALL / 2, B_ISLAND_RECT[1] - TOL)

    def test_old_divider_position_is_rejected(self):
        c = build(VARIANTS["b"])
        c.divider_y = 33.5
        self.assertTrue(any("intersects" in p for p in check(VARIANTS["b"], c)))
