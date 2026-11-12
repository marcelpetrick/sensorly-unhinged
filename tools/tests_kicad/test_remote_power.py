# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prove both VBAT bridges and detect removal of either new landing via."""
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from tools.boardgen import geometry as G

ROOT = Path(__file__).resolve().parents[2]


class RemotePowerConnectivity(unittest.TestCase):
    def test_vbat_depends_on_each_guarded_bridge_via(self):
        with tempfile.TemporaryDirectory(prefix='sensorly-vbat-bridge-') as directory:
            root = Path(directory)
            for key in ('a', 'b'):
                source = ROOT / f'_build/{key}/env-sensor-{key}.kicad_pcb'
                text = source.read_text()
                def opens(board, name):
                    output = root / f'{key}-{name}.json'
                    subprocess.run([os.environ.get('KICAD_CLI','kicad-cli'),'pcb','drc',
                                    '--refill-zones','--format','json','-o',str(output),str(board)],
                                   check=True,capture_output=True,timeout=120)
                    return [c for c in json.loads(output.read_text())['unconnected_items']
                            if any('[VBAT]' in i['description'] for i in c['items'])]
                self.assertEqual(opens(source, 'good'), [])
                for number, point in enumerate(((122.2,73.2),
                        (121.5,90.4) if key=='a' else (119.0,88.8))):
                    candidates=[]
                    for via in G._blocks(text,'via'):
                        at=re.search(r'\(at ([-\d.]+) ([-\d.]+)\)',via)
                        if at and math.dist(tuple(map(float,at.groups())),point)<1e-7 and re.search(r'\(net(?: \d+)? "VBAT"\)',via):
                            candidates.append(via)
                    self.assertEqual(len(candidates),1)
                    broken=root/f'{key}-{number}.kicad_pcb'
                    broken.write_text(text.replace(candidates[0],'',1))
                    for extension in ('kicad_pro','kicad_dru'):
                        shutil.copy2(source.with_suffix('.'+extension),broken.with_suffix('.'+extension))
                    with self.subTest(variant=key,via=point):
                        self.assertEqual(len(opens(broken,str(number))),1)
