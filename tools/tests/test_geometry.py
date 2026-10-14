# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
import re
from dataclasses import replace
from tools.boardgen.geometry import load
from tools.boardgen import geometry as G
from tools.boardgen.check import check
from tools.boardgen.place import place
from tools.boardgen.variants import VARIANTS


class GeometryTests(unittest.TestCase):
    def test_branch_and_layer_segments_have_distinct_stable_ids(self):
        from tools.boardgen.pcb import _tracks
        from tools.boardgen.route import Track
        tracks = [Track("VBAT", 0.4, "F.Cu", [(2, 3), (4, 3)]),
                  Track("VBAT", 0.4, "B.Cu", [(2, 3), (4, 3)]),
                  Track("VBAT", 0.4, "F.Cu", [(2, 3), (2, 5)])]
        source = _tracks(tracks, [], {"VBAT": 1})
        identifiers = re.findall(r'\(uuid "([^"]+)"\)', source)
        self.assertEqual(len(identifiers), 3)
        self.assertEqual(len(set(identifiers)), 3)
        self.assertEqual(source, _tracks(tracks, [], {"VBAT": 1}))

    def test_module_pad_local_rotation_changes_obstacle_extent(self):
        fp = load("ESP32-C6-MINI-1")
        self.assertEqual(fp.pad_size["1"], (0.8, 0.4))
        self.assertEqual(fp.pad_size["12"], (0.4, 0.8))
        self.assertEqual(fp.pad_size["23"], (0.4, 0.8))

    def test_repeated_usb_shield_lugs_keep_largest_extent(self):
        fp = load("USB_C_Receptacle_HRO_TYPE-C-31-M-12")
        self.assertEqual(len(fp.pads["SH"]), 4)
        self.assertEqual(fp.pad_size["SH"], (1.0, 2.1))

    def test_usb_mouth_faces_case_opening_at_manufacturer_edge(self):
        # HRO drawing: front body y=3.65, PCB edge y=3.19.
        for variant in VARIANTS.values():
            placed = place(variant)
            usb = next(p for p in placed if p.ref == "J1")
            mouth = G.xform(0, 3.65, usb.x, usb.y, usb.rot)
            self.assertAlmostEqual(mouth[0], -0.46)
            self.assertEqual([f for f in check(variant, placed) if f.severity == "ERROR"], [])
            # Original placement fit the board but faced away from the opening.
            wrong = replace(usb, x=5.5, rot=90,
                            box=G.placed_box(G.get(usb.footprint), 5.5, usb.y, 90))
            findings = check(variant, [wrong if p.ref == "J1" else p for p in placed])
            self.assertTrue(any(f.rule == "usb-edge-orientation" for f in findings))
