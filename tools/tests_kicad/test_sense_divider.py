# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the R15-to-C13 sense branch on both actual filled layouts."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SenseDividerTests(unittest.TestCase):
    def test_c13_joins_r15_without_new_copper_violations(self):
        with tempfile.TemporaryDirectory(prefix="sensorly-sense-divider-") as d:
            for key in ("a", "b"):
                board = ROOT / f"_build/{key}/env-sensor-{key}.kicad_pcb"
                report = Path(d) / f"{key}.json"
                subprocess.run(
                    [os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                     "--refill-zones", "--format", "json", "-o", str(report), str(board)],
                    check=True, capture_output=True, timeout=120)
                result = json.loads(report.read_text())
                with self.subTest(variant=key):
                    self.assertEqual(result["violations"], [])
                    self.assertFalse(any(
                        "Pad 1 [VBAT_SENSE] of C13" in item["description"]
                        for connection in result["unconnected_items"]
                        for item in connection["items"]),
                        "C13.1 is separate from the R15.1 sense branch")

                # Remove only the reviewed middle leg. KiCad must rediscover
                # the open branch, so the positive check cannot pass merely
                # because an unrelated path joined the same two pads.
                x0, x1 = ((124.04, 126.57) if key == "a"
                          else (121.54, 124.07))
                pattern = (r"\n\t\(segment\n\t\t\(start " + str(x0) +
                           r" 90\.2\)\n\t\t\(end " + str(x1) +
                           r" 90\.2\).*?\n\t\)")
                cut, removed = re.subn(pattern, "", board.read_text(), flags=re.S)
                self.assertEqual(removed, 1)
                broken = Path(d) / f"env-sensor-{key}.kicad_pcb"
                broken.write_text(cut)
                for ext in ("kicad_pro", "kicad_dru"):
                    shutil.copy2(board.with_suffix(f".{ext}"), broken.with_suffix(f".{ext}"))
                broken_report = Path(d) / f"{key}-broken.json"
                subprocess.run(
                    [os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                     "--refill-zones", "--format", "json", "-o",
                     str(broken_report), str(broken)],
                    check=True, capture_output=True, timeout=120)
                broken_result = json.loads(broken_report.read_text())
                with self.subTest(variant=key, missing_middle_leg=True):
                    def sense_opens(report):
                        return sum(any("[VBAT_SENSE]" in item["description"]
                                       for item in connection["items"])
                                   for connection in report["unconnected_items"])
                    self.assertEqual(sense_opens(broken_result),
                                     sense_opens(result) + 1,
                                     "Removing the reviewed leg must add one sense airwire")
