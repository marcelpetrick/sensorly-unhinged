# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check actual pad connectivity and clearance for the fixed U3 controls."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.boardgen.control import route_local_controls
from tools.boardgen.design import NETS
from tools.boardgen.pcb import emit, write
from tools.boardgen.place import place
from tools.boardgen.power import route_local_power
from tools.boardgen.project import write_all
from tools.boardgen.route import route_island
from tools.boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[2]


class RegulatorControlTests(unittest.TestCase):
    def test_actual_pad_paths_are_connected_and_clear(self):
        with tempfile.TemporaryDirectory(prefix="sensorly-control-positive-") as d:
            directory = Path(d)
            shutil.copytree(ROOT / "hardware/lib", directory / "hardware/lib")
            for key, variant in VARIANTS.items():
                placed = place(variant)
                tracks, vias = route_island(variant, placed, NETS)
                for added_tracks, added_vias in (route_local_power(variant, placed),
                                                 route_local_controls(placed)):
                    tracks += added_tracks
                    vias += added_vias
                write_all(directory, variant)
                board = directory / f"hardware/variant-{key}/env-sensor-{key}.kicad_pcb"
                write(board, emit(variant, placed, tracks, vias))
                report = directory / f"{key}.json"
                subprocess.run([os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                                "--refill-zones", "--format", "json", "-o", str(report), str(board)],
                               check=True, capture_output=True, timeout=120)
                result = json.loads(report.read_text())
                with self.subTest(variant=key):
                    self.assertEqual(result["violations"], [])
                    for connection in result["unconnected_items"]:
                        self.assertFalse(any(net in item["description"]
                                             for net in ("[EN_REG]", "[VSET]")
                                             for item in connection["items"]), connection)
