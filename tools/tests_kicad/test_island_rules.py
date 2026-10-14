# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Negative controls: KiCad itself must reject forbidden island copper."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class IslandRuleTests(unittest.TestCase):
    def violations(self, net, width, via_at=None):
        with tempfile.TemporaryDirectory(prefix="sensorly-drc-test-") as d:
            directory = Path(d)
            stem = "env-sensor-b"
            for suffix in ("kicad_pcb", "kicad_pro", "kicad_dru"):
                shutil.copyfile(ROOT / f"_build/b/{stem}.{suffix}", directory / f"{stem}.{suffix}")
            shutil.copyfile(ROOT / "_build/b/fp-lib-table", directory / "fp-lib-table")
            pcb = directory / f"{stem}.kicad_pcb"
            source = pcb.read_text().rstrip()
            self.assertTrue(source.endswith(")"))
            # B.Cu avoids touching the existing F.Cu traces, which KiCad can
            # otherwise use to reassociate an overlapping test segment's net.
            segment = (f'(segment (start 114 96) (end 114 99) (width {width}) '
                       f'(layer "B.Cu") (net "{net}") '
                       '(uuid "d4b9a941-e7bc-4a72-84f2-182ea326870b"))')
            if via_at is not None:
                x, y = via_at
                segment = (f'(via (at {x} {y}) (size 0.6) (drill 0.3) '
                           f'(layers "F.Cu" "B.Cu") (net "{net}") '
                           '(uuid "d4b9a941-e7bc-4a72-84f2-182ea326870b"))')
            pcb.write_text(source[:-1] + segment + "\n)\n")
            report = directory / "drc.json"
            subprocess.run([os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                            "--format", "json", "-o", str(report), str(pcb)],
                           check=True, capture_output=True, timeout=120)
            return json.loads(report.read_text())["violations"]

    def test_generated_island_routes_have_no_kicad_errors(self):
        # Isolate the generator-owned island copper so its package/power
        # clearances are checked even while main-board routing is incomplete.
        from tools.boardgen.variants import VARIANTS
        from tools.boardgen.place import place
        from tools.boardgen.route import route_island, validate_neck_crossings
        from tools.boardgen.design import NETS
        from tools.boardgen.pcb import emit, write
        from tools.boardgen.project import write_all
        with tempfile.TemporaryDirectory(prefix="sensorly-island-positive-") as d:
            directory = Path(d)
            shutil.copytree(ROOT / "hardware/lib", directory / "hardware/lib")
            for key, variant in VARIANTS.items():
                placed = place(variant)
                tracks, vias = route_island(variant, placed, NETS)
                validate_neck_crossings(variant, tracks)
                write_all(directory, variant)
                board = directory / f"hardware/variant-{key}/env-sensor-{key}.kicad_pcb"
                write(board, emit(variant, placed, tracks, vias))
                report = directory / f"island-{key}.json"
                subprocess.run([os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                                "--refill-zones", "--format", "json", "-o", str(report), str(board)],
                               check=True, capture_output=True, timeout=120)
                errors = [v for v in json.loads(report.read_text())["violations"]
                          if v["severity"] == "error"]
                with self.subTest(variant=key):
                    self.assertEqual(errors, [])

    def test_usb_pair_naming_enables_uncoupled_length_rule(self):
        with tempfile.TemporaryDirectory(prefix="sensorly-usb-drc-") as d:
            directory = Path(d)
            stem = "env-sensor-b"
            for suffix in ("kicad_pcb", "kicad_pro", "kicad_dru"):
                source = (ROOT / f"_build/b/{stem}.{suffix}").read_text()
                # Older filled test inputs can exist before main-board regen.
                source = source.replace("USB_DP", "USB_D_P").replace("USB_DM", "USB_D_N")
                (directory / f"{stem}.{suffix}").write_text(source)
            shutil.copyfile(ROOT / "_build/b/fp-lib-table", directory / "fp-lib-table")
            pcb = directory / f"{stem}.kicad_pcb"
            source = pcb.read_text().rstrip()
            segments = '\n'.join(
                f'(segment (start 102 {y}) (end 108 {y}) (width 0.15) '
                f'(layer "B.Cu") (net "{net}") '
                f'(uuid "f2d00105-765b-4c02-97ba-00000000000{i}"))'
                for i, (net, y) in enumerate((("USB_D_P", 78), ("USB_D_N", 80))))
            pcb.write_text(source[:-1] + segments + "\n)\n")
            report = directory / "drc.json"
            subprocess.run([os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                            "--format", "json", "-o", str(report), str(pcb)],
                           check=True, capture_output=True, timeout=120)
            violations = json.loads(report.read_text())["violations"]
            self.assertTrue(any(v["type"] == "diff_pair_uncoupled_length_too_long"
                                for v in violations), violations)

    def test_vbat_cannot_use_power_class_to_enter_neck(self):
        violations = self.violations("VBAT", .15)
        self.assertTrue(any(v["type"] == "items_not_allowed" and
                            "nothing but the sensor nets crosses the neck" in v["description"]
                            for v in violations), violations)

    def test_ground_track_cannot_be_widened(self):
        violations = self.violations("GND", .30)
        self.assertTrue(any(v["type"] == "track_width" and
                            "all four island tracks stay thin" in v["description"]
                            for v in violations), violations)

    def test_sensor_via_stays_out_of_neck(self):
        violations = self.violations("SDA", .15, via_at=(114, 97))
        self.assertTrue(any(v["type"] == "items_not_allowed" and
                            "no vias in the sensor thermal area" in v["description"]
                            for v in violations), violations)

    def test_main_board_sensor_via_is_not_globally_forbidden(self):
        violations = self.violations("SDA", .15, via_at=(126, 80))
        self.assertFalse(any(v["type"] == "items_not_allowed" and
                             "no vias in the sensor" in v["description"]
                             for v in violations), violations)

    def test_package_body_keepout_survives_library_zone_removal(self):
        violations = self.violations("GND", .15, via_at=(115, 106))
        self.assertTrue(any(v["type"] == "items_not_allowed" and
                            "Sensor package keepout U2" in v["description"]
                            for v in violations), violations)

    def test_antenna_keepout_survives_library_zone_removal(self):
        violations = self.violations("GND", .15, via_at=(115, 63))
        self.assertTrue(any(v["type"] == "items_not_allowed" and
                            "RF keep-out" in v["description"]
                            for v in violations), violations)
