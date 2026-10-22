# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""KiCad controls: only explicit power escape corridors permit narrow traces."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.boardgen.geometry import _blocks
from tools.boardgen.pcb import _zone
from tools.boardgen.project import dru
from tools.boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[2]
TEST_UUID = "96d1cabb-7ecf-4b77-8c56-7b0a39881ca3"


class PowerRuleTests(unittest.TestCase):
    def width_violations(self, width, corridor=False, extends=False):
        with tempfile.TemporaryDirectory(prefix="sensorly-power-drc-") as d:
            directory = Path(d)
            stem = "env-sensor-b"
            for suffix in ("kicad_pcb", "kicad_pro"):
                shutil.copyfile(ROOT / f"_build/b/{stem}.{suffix}", directory / f"{stem}.{suffix}")
            (directory / f"{stem}.kicad_dru").write_text(dru(VARIANTS["b"]))
            pcb = directory / f"{stem}.kicad_pcb"
            source = pcb.read_text().rstrip()
            # Isolate the injected width control from production copper and
            # areas, whose position legitimately changes with routing.
            for head in ("segment", "via", "zone"):
                for block in list(_blocks(source, head)):
                    source = source.replace(block, "")
            segment = (f'(segment (start 102 90) (end {104 if extends else 103} 90) '
                       f'(width {width}) (layer "B.Cu") (net "VBAT") '
                       f'(uuid "{TEST_UUID}"))')
            if corridor:
                segment += _zone("Power escape injected test", "", {}, ["B.Cu"],
                    [(1.8,29.8),(3.2,29.8),(3.2,30.2),(1.8,30.2)],
                    "test/power-escape", keepout=dict(tracks="allowed",vias="allowed",
                    pads="allowed",copperpour="allowed",footprints="allowed"))
            pcb.write_text(source[:-1] + segment + "\n)\n")
            report = directory / "drc.json"
            subprocess.run([os.environ.get("KICAD_CLI", "kicad-cli"), "pcb", "drc",
                            "--format", "json", "-o", str(report), str(pcb)],
                           check=True, capture_output=True, timeout=120)
            return [v for v in json.loads(report.read_text())["violations"]
                    if v["type"] == "track_width" and
                    any(i["uuid"] == TEST_UUID for i in v["items"])]

    def test_narrow_power_trunk_is_rejected(self):
        self.assertTrue(self.width_violations(.2))

    def test_full_width_power_trunk_is_accepted(self):
        self.assertFalse(self.width_violations(.4))

    def test_bounded_neckdown_is_accepted(self):
        self.assertFalse(self.width_violations(.15, corridor=True))

    def test_partial_corridor_overlap_does_not_relax_power_width(self):
        self.assertTrue(self.width_violations(.15, corridor=True, extends=True))


class SwitchRuleTests(unittest.TestCase):
    def violations(self, width=.6, layer='F.Cu', corridor=False, extends=False, via=False):
        with tempfile.TemporaryDirectory(prefix='sensorly-switch-drc-') as d:
            directory=Path(d);stem='env-sensor-b'
            for suffix in ('kicad_pcb','kicad_pro'):
                shutil.copyfile(ROOT/f'_build/b/{stem}.{suffix}',directory/f'{stem}.{suffix}')
            (directory/f'{stem}.kicad_dru').write_text(dru(VARIANTS['b']))
            board=directory/f'{stem}.kicad_pcb';source=board.read_text().rstrip()
            for head in ('segment','via','zone','footprint'):
                for block in list(_blocks(source,head)):source=source.replace(block,'')
            item=(f'(via (at 102 90) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net "SW_L") (uuid "{TEST_UUID}"))' if via else
                  f'(segment (start 102 90) (end {104 if extends else 103} 90) (width {width}) (layer "{layer}") (net "SW_L") (uuid "{TEST_UUID}"))')
            if corridor:
                item+=_zone('Switch escape injected test','',{},['F.Cu'],[(1.8,29.8),(3.2,29.8),(3.2,30.2),(1.8,30.2)],'test/switch-escape',
                    keepout=dict(tracks='allowed',vias='allowed',pads='allowed',copperpour='allowed',footprints='allowed'))
            board.write_text(source[:-1]+item+'\n)\n');report=directory/'drc.json'
            subprocess.run([os.environ.get('KICAD_CLI','kicad-cli'),'pcb','drc','--format','json','-o',str(report),str(board)],check=True,capture_output=True,timeout=120)
            return [v for v in json.loads(report.read_text())['violations'] if any(i['uuid']==TEST_UUID for i in v['items'])]
    def test_full_width_top_trunk_is_accepted(self):
        self.assertFalse([v for v in self.violations() if v['type'] in ('track_width','items_not_allowed')])
    def test_narrow_trunk_outside_corridor_is_rejected(self):
        self.assertTrue([v for v in self.violations(.15) if v['type']=='track_width'])
    def test_narrow_trunk_inside_corridor_is_accepted(self):
        self.assertFalse([v for v in self.violations(.15,corridor=True) if v['type']=='track_width'])
    def test_partly_outside_corridor_is_rejected(self):
        self.assertTrue([v for v in self.violations(.15,corridor=True,extends=True) if v['type']=='track_width'])
    def test_non_top_switch_copper_is_rejected(self):
        for layer in ('B.Cu','In1.Cu','In2.Cu'):
            with self.subTest(layer=layer):self.assertTrue([v for v in self.violations(layer=layer) if v['type']=='items_not_allowed'])
    def test_switch_via_is_rejected(self):
        self.assertTrue([v for v in self.violations(via=True) if v['type']=='items_not_allowed'])
    def test_reviewed_local_power_and_sensor_routes_are_clear_on_both_boards(self):
        from tools.boardgen.check import check
        from tools.boardgen.place import place
        from tools.boardgen.power import route_local_power
        from tools.boardgen.route import route_island,validate_neck_crossings
        from tools.boardgen.design import NETS
        from tools.boardgen.pcb import emit,write
        from tools.boardgen.project import write_all
        with tempfile.TemporaryDirectory(prefix='sensorly-local-power-positive-') as d:
            directory=Path(d)
            shutil.copytree(ROOT/'hardware/lib',directory/'hardware/lib')
            for key,variant in VARIANTS.items():
                placed=place(variant)
                self.assertFalse([f for f in check(variant,placed) if f.severity=='ERROR'])
                tracks,vias=route_island(variant,placed,NETS)
                local_t,local_v=route_local_power(variant,placed)
                tracks+=local_t;vias+=local_v
                validate_neck_crossings(variant,tracks)
                write_all(directory,variant)
                board=directory/f'hardware/variant-{key}/env-sensor-{key}.kicad_pcb'
                write(board,emit(variant,placed,tracks,vias))
                report=directory/f'{key}.json'
                subprocess.run([os.environ.get('KICAD_CLI','kicad-cli'),'pcb','drc','--refill-zones','--format','json','-o',str(report),str(board)],check=True,capture_output=True,timeout=120)
                with self.subTest(variant=key):self.assertEqual(json.loads(report.read_text())['violations'],[])
