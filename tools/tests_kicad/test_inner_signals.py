# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""New signal connectivity depends on real inner copper, not net labels."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from tools.boardgen import geometry as G

ROOT=Path(__file__).resolve().parents[2]


class InnerSignalConnectivity(unittest.TestCase):
    def test_cut_each_new_inner_bridge_restores_its_airwire(self):
        with tempfile.TemporaryDirectory(prefix='sensorly-inner-bridge-') as directory:
            root=Path(directory)
            for key,net in (('a','CHG_N'),('b','SDA'),('b','PACK_TS_SENSE'),('b','VBAT_SENSE')):
                source=ROOT/f'_build/{key}/env-sensor-{key}.kicad_pcb'
                text=source.read_text()
                def opens(board,name):
                    output=root/f'{key}-{net}-{name}.json'
                    subprocess.run([os.environ.get('KICAD_CLI','kicad-cli'),'pcb','drc',
                                    '--refill-zones','--format','json','-o',str(output),str(board)],
                                   check=True,capture_output=True,timeout=120)
                    return [c for c in json.loads(output.read_text())['unconnected_items']
                            if any(f'[{net}]' in i['description'] for i in c['items'])]
                self.assertEqual(opens(source,'good'),[])
                targets=[segment for segment in G._blocks(text,'segment')
                         if '(layer "In2.Cu")' in segment and re.search(r'\(net(?: \d+)? "'+re.escape(net)+r'"\)',segment)]
                self.assertTrue(targets)
                for segment in targets:text=text.replace(segment,'',1)
                broken=root/f'{key}-{net}.kicad_pcb'
                broken.write_text(text)
                for extension in ('kicad_pro','kicad_dru'):
                    shutil.copy2(source.with_suffix('.'+extension),broken.with_suffix('.'+extension))
                with self.subTest(variant=key,net=net):
                    self.assertEqual(len(opens(broken,'broken')),1)

    def test_compact_supply_feed_depends_on_its_outer_bridge(self):
        import math
        source=ROOT/'_build/a/env-sensor-a.kicad_pcb'
        text=source.read_text()
        targets=[]
        for segment in G._blocks(text,'segment'):
            if '(layer "B.Cu")' not in segment or not re.search(r'\(net(?: \d+)? "\+3V0"\)',segment):continue
            points=[tuple(map(float,p)) for p in re.findall(r'\((?:start|end) ([-\d.]+) ([-\d.]+)\)',segment)]
            if any(math.dist(point,(107.4,69.1))<1e-7 for point in points):targets.append(segment)
        self.assertEqual(len(targets),1)
        with tempfile.TemporaryDirectory(prefix='sensorly-inner-supply-') as directory:
            root=Path(directory)
            def opens(board,name):
                output=root/f'{name}.json'
                subprocess.run([os.environ.get('KICAD_CLI','kicad-cli'),'pcb','drc',
                                '--refill-zones','--format','json','-o',str(output),str(board)],
                               check=True,capture_output=True,timeout=120)
                return sum(any('[+3V0]' in item['description'] for item in row['items'])
                           for row in json.loads(output.read_text())['unconnected_items'])
            before=opens(source,'good')
            broken=root/'broken.kicad_pcb';broken.write_text(text.replace(targets[0],'',1))
            for extension in ('kicad_pro','kicad_dru'):
                shutil.copy2(source.with_suffix('.'+extension),broken.with_suffix('.'+extension))
            self.assertEqual(opens(broken,'broken'),before+1)
