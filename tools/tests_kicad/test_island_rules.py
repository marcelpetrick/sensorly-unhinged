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
    def violations(self, net, width):
        with tempfile.TemporaryDirectory(prefix="sensorly-drc-test-") as d:
            directory = Path(d)
            stem = "env-sensor-b"
            for suffix in ("kicad_pcb", "kicad_pro", "kicad_dru"):
                shutil.copyfile(ROOT / f"_build/b/{stem}.{suffix}", directory / f"{stem}.{suffix}")
            pcb = directory / f"{stem}.kicad_pcb"
            source = pcb.read_text().rstrip()
            self.assertTrue(source.endswith(")"))
            # Absolute board coordinates: x=114, y=96..99 lies in B's neck.
            segment = (f'(segment (start 114 96) (end 114 99) (width {width}) '
                       f'(layer "F.Cu") (net "{net}") '
                       '(uuid "d4b9a941-e7bc-4a72-84f2-182ea326870b"))')
            pcb.write_text(source[:-1] + segment + "\n)\n")
            report = directory / "drc.json"
            subprocess.run([os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                            "--format", "json", "-o", str(report), str(pcb)],
                           check=True, capture_output=True, timeout=120)
            return json.loads(report.read_text())["violations"]

    def test_vbat_cannot_use_power_class_to_enter_neck(self):
        violations = self.violations("VBAT", .15)
        self.assertTrue(any(v["type"] == "disallowed_items" for v in violations), violations)

    def test_ground_track_cannot_be_widened(self):
        violations = self.violations("GND", .30)
        self.assertTrue(any(v["type"] == "track_width" and
                            "all four island tracks stay thin" in v["description"]
                            for v in violations), violations)
