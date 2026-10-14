# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""KiCad controls: only explicit power escape corridors permit narrow traces."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.boardgen.geometry import _blocks
from tools.boardgen.pcb import _zone
from tools.boardgen.project import dru
from tools.boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[2]
TEST_UUID = "96d1cabb-7ecf-4b77-8c56-7b0a39881ca3"


class PowerRuleTests(unittest.TestCase):
    def width_violations(self, width, corridor=False, extends=False):
        with tempfile.TemporaryDirectory(prefix="sensorly-power-drc-") as d:
            directory = Path(d)
            stem = "env-sensor-b"
            for suffix in ("kicad_pcb", "kicad_pro"):
                shutil.copyfile(ROOT / f"_build/b/{stem}.{suffix}", directory / f"{stem}.{suffix}")
            (directory / f"{stem}.kicad_dru").write_text(dru(VARIANTS["b"]))
            pcb = directory / f"{stem}.kicad_pcb"
            source = pcb.read_text().rstrip()
            # Isolate the injected width control from production copper and
            # areas, whose position legitimately changes with routing.
            for head in ("segment", "via", "zone"):
                for block in list(_blocks(source, head)):
                    source = source.replace(block, "")
            segment = (f'(segment (start 102 90) (end {104 if extends else 103} 90) '
                       f'(width {width}) (layer "B.Cu") (net "VBAT") '
                       f'(uuid "{TEST_UUID}"))')
            if corridor:
                segment += _zone("Power escape injected test", "", {}, ["B.Cu"],
                    [(1.8,29.8),(3.2,29.8),(3.2,30.2),(1.8,30.2)],
                    "test/power-escape", keepout=dict(tracks="allowed",vias="allowed",
                    pads="allowed",copperpour="allowed",footprints="allowed"))
            pcb.write_text(source[:-1] + segment + "\n)\n")
            report = directory / "drc.json"
            subprocess.run([os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                            "--format", "json", "-o", str(report), str(pcb)],
                           check=True, capture_output=True, timeout=120)
            return [v for v in json.loads(report.read_text())["violations"]
                    if v["type"] == "track_width" and
                    any(i["uuid"] == TEST_UUID for i in v["items"])]

    def test_narrow_power_trunk_is_rejected(self):
        self.assertTrue(self.width_violations(.2))

    def test_full_width_power_trunk_is_accepted(self):
        self.assertFalse(self.width_violations(.4))

    def test_bounded_neckdown_is_accepted(self):
        self.assertFalse(self.width_violations(.15, corridor=True))

    def test_partial_corridor_overlap_does_not_relax_power_width(self):
        self.assertTrue(self.width_violations(.15, corridor=True, extends=True))
