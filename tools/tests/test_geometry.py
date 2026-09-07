# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from tools.boardgen.geometry import load


class GeometryTests(unittest.TestCase):
    def test_repeated_usb_shield_lugs_keep_largest_extent(self):
        fp = load("USB_C_Receptacle_HRO_TYPE-C-31-M-12")
        self.assertEqual(len(fp.pads["SH"]), 4)
        self.assertEqual(fp.pad_size["SH"], (1.0, 2.1))
