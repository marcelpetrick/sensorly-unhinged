# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path

from tools.boardgen.enclosure import (
    BATT_Z, BATT_Z_ALLOW, SUPPORT_H, build, check, planning_cell_fits,
    ROOT, scad_params,
    HEIGHTS, TOL, WALL, USB_SHELL_H, USB_SHELL_W,
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

    def test_three_clamps_avoid_components_and_stay_on_body(self):
        for v in VARIANTS.values():
            c = build(v)
            self.assertGreaterEqual(len(c.edge_holddowns), 3)
            self.assertEqual({side for side, _ in c.edge_holddowns}, {"left", "right"})
            self.assertEqual(check(v, c), [])

    def test_sensor_island_retention_is_rejected(self):
        c = build(VARIANTS["b"])
        c.edge_holddowns.append(("left", B_ISLAND_RECT[1] + 2))
        self.assertTrue(any("retention region" in p for p in check(VARIANTS["b"], c)))

    def test_connector_overlap_is_rejected(self):
        c = build(VARIANTS["b"])
        c.edge_holddowns.append(("left", 24.5))
        self.assertTrue(any("overlaps" in p for p in check(VARIANTS["b"], c)))

    def test_side_switch_has_no_misleading_top_actuator_hole(self):
        for v in VARIANTS.values():
            self.assertFalse(any(c.ref == "SW1" for c in build(v).cutouts))
        self.assertEqual(HEIGHTS["SW1"][0], 1.95)

    def test_old_narrow_usb_opening_is_rejected(self):
        c = build(VARIANTS["a"])
        usb = next(co for co in c.cutouts if co.ref == "J1")
        usb.width, usb.height = 9.55, 3.51
        self.assertTrue(any("cable shell" in p for p in check(VARIANTS["a"], c)))

    def test_recessed_socket_needs_lid_lip_relief(self):
        c = build(VARIANTS["b"])
        c.lid_port_relief = False
        self.assertTrue(any("lid lip" in p for p in check(VARIANTS["b"], c)))

    def test_original_support_height_loses_cable_battery_separation(self):
        c = build(VARIANTS["a"])
        c.board_z = BATT_Z + BATT_Z_ALLOW + 0.8
        self.assertTrue(any("battery/swelling" in p for p in check(VARIANTS["a"], c)))

    def test_vertical_friction_does_not_count_as_xy_registration(self):
        c = build(VARIANTS["a"])
        c.side_stops = False
        c.usb_guides = []
        self.assertTrue(any("XY registration" in p for p in check(VARIANTS["a"], c)))

    def test_neck_has_clearance_after_xy_stops_engage(self):
        c = build(VARIANTS["b"])
        c.neck_slot = (4.2, c.neck_slot[1])
        self.assertTrue(any("registration travel" in p for p in check(VARIANTS["b"], c)))


@unittest.skipUnless(shutil.which("openscad"), "OpenSCAD required for mesh control")
class CableMeshControls(unittest.TestCase):
    def test_missing_lid_relief_produces_real_cable_collision(self):
        with tempfile.TemporaryDirectory(prefix="sensorly-cable-control-") as d:
            for v in VARIANTS.values():
                c = build(v)
                c.lid_port_relief = False
                path = Path(d) / f"{v.key}.scad"
                output = Path(d) / f"{v.key}.stl"
                path.write_text(scad_params(v, c) + '\ninclude <' +
                                str(ROOT / "mechanical/env-sensor-case.scad") + '>\n')
                result = subprocess.run(["openscad", "-D", 'part="cable_interference"',
                                         "-o", str(output), str(path)],
                                        capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(output.exists(), result.stderr)
