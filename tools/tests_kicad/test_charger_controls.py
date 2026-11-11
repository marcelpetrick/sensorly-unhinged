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
import pcbnew
from tools.boardgen import geometry as G

ROOT = Path(__file__).resolve().parents[2]


def inspect(board, output):
    subprocess.run([os.environ.get('KICAD_CLI', 'kicad-cli'), 'pcb', 'drc',
                    '--refill-zones', '--format', 'json', '-o', str(output), str(board)],
                   check=True, capture_output=True, timeout=120)
    return json.loads(output.read_text())


def opens(result):
    return sum(any('[PACK_TS]' in i['description'] for i in item['items'])
               for item in result['unconnected_items'])


class ChargerEndpointConnectivity(unittest.TestCase):
    def test_actual_u4_to_connector_path_and_missing_trunk(self):
        source = ROOT / '_build/b/env-sensor-b.kicad_pcb'
        with tempfile.TemporaryDirectory(prefix='sensorly-charger-ts-') as d:
            root = Path(d)
            # Keep the real pads and full clearance environment. Only exclude
            # the separate unfinished R21 branch from this two-endpoint proof.
            self.assertEqual(inspect(source, root / "full-source.json")["violations"], [])
            board = pcbnew.LoadBoard(str(source))
            endpoints = set()
            for pad in list(board.GetPads()):
                if pad.GetNetname() != 'PACK_TS':
                    continue
                footprint = pad.GetParentFootprint()
                pair = (footprint.GetReference(), pad.GetNumber())
                if pair in {('U4', '1'), ('J2', '2')}:
                    endpoints.add(pair)
                else:
                    footprint.Remove(pad)
            self.assertEqual(endpoints, {('U4', '1'), ('J2', '2')})
            good = root / source.name
            pcbnew.SaveBoard(str(good), board)
            for ext in ('kicad_pro', 'kicad_dru'):
                shutil.copy2(source.with_suffix('.'+ext), good.with_suffix('.'+ext))
            result = inspect(good, root / 'good.json')
            self.assertEqual(opens(result), 0)
            # Longest B.Cu PACK_TS segment is the real remote trunk; remove it
            # rather than matching a serialization-dependent coordinate string.
            text = good.read_text()
            segments = [block for block in G._blocks(text, 'segment')
                        if '(layer "B.Cu")' in block
                        and re.search(r'\(net(?: \d+)? "PACK_TS"\)', block)]
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
            self.assertEqual(opens(inspect(broken, root / 'broken.json')), 1)
