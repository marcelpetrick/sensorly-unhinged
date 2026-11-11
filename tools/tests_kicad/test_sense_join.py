# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""KiCad confirms the sense divider top pad joins its capacitor branch."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SenseJoinTests(unittest.TestCase):
    def test_r14_r15_join_and_deletion_control(self):
        coordinates = {
            "a": ((122.56, 91), (124.04, 91)),
            "b": ((120.06, 89.75), (121.54, 91)),
        }
        with tempfile.TemporaryDirectory(prefix="sensorly-sense-join-") as d:
            for variant, (start, end) in coordinates.items():
                board = ROOT / f"_build/{variant}/env-sensor-{variant}.kicad_pcb"

                def report(path, name):
                    output = Path(d) / f"{variant}-{name}.json"
                    subprocess.run(
                        [os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                         "--refill-zones", "--schematic-parity", "--format", "json",
                         "-o", str(output), str(path)],
                        check=True, capture_output=True, timeout=120)
                    return json.loads(output.read_text())

                def sense_opens(result):
                    return sum(any("[VBAT_SENSE]" in item["description"]
                                   for item in connection["items"])
                               for connection in result["unconnected_items"])

                present = report(board, "present")
                with self.subTest(variant=variant):
                    self.assertEqual(present["violations"], [])
                    pattern = (r"\n\t\(segment\n\t\t\(start " +
                               re.escape(f"{start[0]} {start[1]}") +
                               r"\)\n\t\t\(end " +
                               re.escape(f"{end[0]} {end[1]}") +
                               r"\)\n\t\t\(width 0\.15\)\n"
                               r"\t\t\(layer \"F\.Cu\"\)\n"
                               r"\t\t\(net \"VBAT_SENSE\"\).*?\n\t\)")
                    cut, removed = re.subn(pattern, "", board.read_text(), flags=re.S)
                    self.assertEqual(removed, 1)
                    broken = Path(d) / f"env-sensor-{variant}.kicad_pcb"
                    broken.write_text(cut)
                    for ext in ("kicad_pro", "kicad_dru"):
                        shutil.copy2(board.with_suffix(f".{ext}"), broken.with_suffix(f".{ext}"))
                    self.assertEqual(sense_opens(report(broken, "broken")),
                                     sense_opens(present) + 1)
