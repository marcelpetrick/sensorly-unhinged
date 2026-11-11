# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual two-endpoint thermistor connectivity and deleted-copper control."""
import json
import os
import math
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from tools.boardgen import geometry as G

ROOT = Path(__file__).resolve().parents[2]


def inspect(board, output):
    subprocess.run([os.environ.get('KICAD_CLI', 'kicad-cli'), 'pcb', 'drc',
                    '--refill-zones', '--format', 'json', '-o', str(output), str(board)],
                   check=True, capture_output=True, timeout=120)
    return json.loads(output.read_text())


def opens(result, net):
    return sum(any(f'[{net}]' in i['description'] for i in item['items'])
               for item in result['unconnected_items'])


class ChargerEndpointConnectivity(unittest.TestCase):
    def test_actual_u4_to_connector_path_and_missing_trunk(self):
        self.prove_path('b', 'PACK_TS', {('U4', '1'), ('J2', '2')})

    def test_actual_transistor_to_pullup_path_and_missing_trunk(self):
        self.prove_path('a', 'CHARGE_EN_N', {('Q1', '3'), ('R18', '1')})

    def test_actual_enable_gate_to_pulldown_path_and_missing_trunk(self):
        self.prove_path('a', 'CHARGE_ENABLE', {('Q1', '1'), ('R7', '1')})

    def test_actual_compact_status_path_and_missing_trunk(self):
        self.prove_path('a', 'CHG_N', {('U4', '9'), ('R10', '2')})

    def test_actual_isolated_status_fixture_path_and_missing_trunk(self):
        self.prove_path('b', 'CHG_N', {('TP14', '1'), ('R10', '2')})

    def prove_path(self, key, net, wanted):
        source = ROOT / f'_build/{key}/env-sensor-{key}.kicad_pcb'
        with tempfile.TemporaryDirectory(prefix='sensorly-charger-ts-') as d:
            root = Path(d)
            # Keep the real pads and full clearance environment. Only exclude
            # the separate unfinished R21 branch from this two-endpoint proof.
            self.assertEqual(inspect(source, root / "full-source.json")["violations"], [])
            text = source.read_text()
            net_pattern = r'\(net(?: \d+)? "' + re.escape(net) + r'"\)'
            endpoints = set()
            for footprint in G._blocks(text, 'footprint'):
                if not footprint.startswith('(footprint "'):
                    continue
                ref = re.search(r'\(property "Reference" "([^"]+)"', footprint).group(1)
                filtered = footprint
                for pad in G._blocks(footprint, 'pad'):
                    if not re.search(net_pattern, pad):
                        continue
                    number = re.search(r'^\(pad "([^"]+)"', pad).group(1)
                    pair = (ref, number)
                    if pair in wanted:
                        endpoints.add(pair)
                    else:
                        filtered = filtered.replace(pad, '', 1)
                text = text.replace(footprint, filtered, 1)
            self.assertEqual(endpoints, wanted)
            good = root / source.name
            good.write_text(text)
            for ext in ('kicad_pro', 'kicad_dru'):
                shutil.copy2(source.with_suffix('.'+ext), good.with_suffix('.'+ext))
            result = inspect(good, root / 'good.json')
            self.assertEqual(opens(result, net), 0)
            # Longest B.Cu PACK_TS segment is the real remote trunk; remove it
            # rather than matching a serialization-dependent coordinate string.
            text = good.read_text()
            segments = [block for block in G._blocks(text, 'segment')
                        if '(layer "B.Cu")' in block
                        and re.search(r'\(net(?: \d+)? "' + re.escape(net) + r'"\)', block)]
            self.assertTrue(segments)
            def length(block):
                start = re.search(r'\(start ([^ ]+) ([^)]+)\)', block)
                end = re.search(r'\(end ([^ ]+) ([^)]+)\)', block)
                return math.dist(tuple(map(float, start.groups())),
                                 tuple(map(float, end.groups())))
            broken = root / 'broken.kicad_pcb'
            broken.write_text(text.replace(max(segments, key=length), '', 1))
            for ext in ('kicad_pro', 'kicad_dru'):
                shutil.copy2(source.with_suffix('.'+ext), broken.with_suffix('.'+ext))
            self.assertEqual(opens(inspect(broken, root / 'broken.json'), net), 1)
