# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that actual filled copper joins every GND region on both variants."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class GroundConnectivityTests(unittest.TestCase):
    def test_filled_boards_have_no_isolated_ground_regions(self):
        with tempfile.TemporaryDirectory(prefix='sensorly-ground-connectivity-') as d:
            for key in ('a', 'b'):
                board = ROOT / f'_build/{key}/env-sensor-{key}.kicad_pcb'
                report = Path(d) / f'{key}.json'
                subprocess.run([os.environ.get('KICAD_CLI', 'kicad-cli'), 'pcb', 'drc',
                                '--refill-zones', '--format', 'json', '-o', str(report),
                                str(board)], check=True, capture_output=True, timeout=120)
                result = json.loads(report.read_text())
                with self.subTest(variant=key):
                    self.assertEqual(result['violations'], [])
                    ground = [connection for connection in result['unconnected_items']
                              if any('[GND]' in item['description']
                                     for item in connection['items'])]
                    self.assertEqual(ground, [], 'A filled GND region is still isolated')
