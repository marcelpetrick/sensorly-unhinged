# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prove the R22 supply reaches the actual filled plane; cut its via."""
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


class PlaneAccessConnectivity(unittest.TestCase):
    def test_supply_path_depends_on_its_off_paste_via(self):
        with tempfile.TemporaryDirectory(prefix='sensorly-pullup-plane-') as d:
            root = Path(d)
            for key in ('a', 'b'):
                source = ROOT / f'_build/{key}/env-sensor-{key}.kicad_pcb'
                text = source.read_text()
                endpoints = set()
                for footprint in G._blocks(text, 'footprint'):
                    if not footprint.startswith('(footprint "'):
                        continue
                    ref = re.search(r'\(property "Reference" "([^\"]+)"', footprint).group(1)
                    filtered = footprint
                    for pad in G._blocks(footprint, 'pad'):
                        if not re.search(r'\(net(?: \d+)? "\+3V0"\)', pad):
                            continue
                        number = re.search(r'^\(pad "([^\"]+)"', pad).group(1)
                        if (ref, number) in {('R22', '2'), ('U1', '3')}:
                            endpoints.add((ref, number))
                        else:
                            filtered = filtered.replace(pad, '', 1)
                    text = text.replace(footprint, filtered, 1)
                self.assertEqual(endpoints, {('R22', '2'), ('U1', '3')})
                good = root / source.name
                good.write_text(text)
                for ext in ('kicad_pro', 'kicad_dru'):
                    shutil.copy2(source.with_suffix('.'+ext), good.with_suffix('.'+ext))
                def opens(board, name):
                    output = root / f'{key}-{name}.json'
                    subprocess.run([os.environ.get('KICAD_CLI', 'kicad-cli'), 'pcb', 'drc',
                                    '--refill-zones', '--format', 'json', '-o', str(output), str(board)],
                                   check=True, capture_output=True, timeout=120)
                    return sum(any('[+3V0]' in i['description'] for i in c['items'])
                               for c in json.loads(output.read_text())['unconnected_items'])
                with self.subTest(variant=key):
                    self.assertEqual(opens(good, 'good'), 0)
                    target = [block for block in G._blocks(text, 'via')
                              if re.search(r'\(at 100\.8 71\.2\)', block)
                              and re.search(r'\(net(?: \d+)? "\+3V0"\)', block)]
                    self.assertEqual(len(target), 1)
                    broken = root / f'broken-{key}.kicad_pcb'
                    broken.write_text(text.replace(target[0], '', 1))
                    for ext in ('kicad_pro', 'kicad_dru'):
                        shutil.copy2(source.with_suffix('.'+ext), broken.with_suffix('.'+ext))
                    self.assertEqual(opens(broken, 'broken'), 1)
