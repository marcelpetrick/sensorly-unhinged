# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual filled-board EN connectivity depends on the additive fixture branch."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from tools.boardgen import geometry as G

ROOT = Path(__file__).resolve().parents[2]


class FixtureBranchConnectivity(unittest.TestCase):
    def test_reset_branch_and_cut_control_on_both_boards(self):
        # One necessary new layer transition on each candidate, in board coords.
        coordinates = {'a': (124.5, 78.4), 'b': (123.5, 78.7)}
        with tempfile.TemporaryDirectory(prefix='sensorly-fixture-branch-') as directory:
            root = Path(directory)
            for variant, (x,y) in coordinates.items():
                source = ROOT / f'_build/{variant}/env-sensor-{variant}.kicad_pcb'
                text = source.read_text()
                def report(board, label):
                    out = root / f'{variant}-{label}.json'
                    subprocess.run([os.environ.get('KICAD_CLI', 'kicad-cli'), 'pcb', 'drc',
                                    '--refill-zones', '--format', 'json', '-o', str(out), str(board)],
                                   check=True, capture_output=True, timeout=120)
                    return json.loads(out.read_text())
                def opens(result):
                    return sum(any('[EN]' in i['description'] for i in row['items'])
                               for row in result['unconnected_items'])
                with self.subTest(variant=variant):
                    present = report(source, 'present')
                    self.assertEqual(present['violations'], [])
                    self.assertEqual(opens(present), 1)  # different remaining branch stays open
                    target = [block for block in G._blocks(text, 'via')
                              if re.search(r'\(at '+re.escape(f'{x:g} {y:g}')+r'\)', block)
                              and re.search(r'\(net(?: \d+)? "EN"\)', block)]
                    self.assertEqual(len(target), 1)
                    broken = root / source.name
                    broken.write_text(text.replace(target[0], '', 1))
                    for ext in ('kicad_pro','kicad_dru'):
                        shutil.copy2(source.with_suffix('.'+ext), broken.with_suffix('.'+ext))
                    self.assertEqual(opens(report(broken, 'cut')), 2)
