# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual KiCad differential controls, retaining the production default rule."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.boardgen import geometry as G
from tools.boardgen.pcb import emit, _tracks, _net_index
from tools.boardgen.place import place
from tools.boardgen.project import write_all
from tools.boardgen.route import Track
from tools.boardgen.usbroute import route_usb, trunk_areas
from tools.boardgen.variants import VARIANTS

class USBDifferentialRules(unittest.TestCase):
    def report(self, variant, tracks, named_trunks=False):
        p=place(variant)
        # Empty copper emission avoids bypassing the complete USB source guard.
        source=emit(variant,p,[],[])
        for kind in ('footprint','zone'):
            for block in G._blocks(source,kind):source=source.replace(block,'')
        pads=[]
        for i,t in enumerate(tracks):
            for j,(x,y) in enumerate((t.pts[0],t.pts[-1])):
                pads.append(f'(pad "{i}-{j}" smd rect (at {x+100} {y+60}) '
                  f'(size 0.25 0.25) (layers "{t.layer}" "F.Mask") (net "{t.net}"))')
        source=source.rstrip()[:-1]+_tracks(tracks,[],_net_index())
        source+='(footprint "USB test terminals" (layer "F.Cu") (at 0 0) (attr smd) '+''.join(pads)+')'
        if named_trunks:source+=trunk_areas(variant,_net_index(),[])
        source+='\n)\n'
        with tempfile.TemporaryDirectory(prefix='sensorly-usb-topology-') as d:
            root=Path(d);write_all(root,variant)
            board=root/f'hardware/variant-{variant.key}/env-sensor-{variant.key}.kicad_pcb'
            board.write_text(source);report=root/'drc.json'
            subprocess.run([os.environ.get('KICAD_CLI','kicad-cli'),'pcb','drc','--format','json',
              '-o',str(report),str(board)],check=True,capture_output=True,timeout=120)
            return json.loads(report.read_text())['violations']

    def test_actual_paired_trunks_meet_two_mm_rule_both_variants(self):
        for v in VARIANTS.values():
            p=place(v);tracks,_=route_usb(v,p)
            trunks=[t for t in tracks if t.purpose.startswith('usb:trunk-')]
            violations=self.report(v,trunks,True)
            self.assertFalse([x for x in violations if x['severity']=='error'],violations)

    def test_six_mm_divergent_copper_still_fails_default_rule(self):
        t=[Track('USB_D_N',.25,'F.Cu',[(12,20),(18,20)]),
           Track('USB_D_P',.25,'F.Cu',[(12,20.45),(12,26.45)])]
        violations=self.report(VARIANTS['a'],t)
        self.assertTrue(any(x['type']=='diff_pair_uncoupled_length_too_long' for x in violations),violations)

class USBFilledReferenceTests(unittest.TestCase):
    def test_filled_reference_covers_copper_and_transition_returns(self):
        import math
        import pcbnew
        root=Path(__file__).resolve().parents[2]
        for key,v in VARIANTS.items():
            board=pcbnew.LoadBoard(str(root/f'_build/{key}/env-sensor-{key}.kicad_pcb'))
            tracks,vias=route_usb(v,place(v))
            ground=[q for q in vias if q.net=='GND']
            usb_vias=[q for q in vias if q.net.startswith('USB_D_')]
            def covered(x,y,layer):
                point=pcbnew.VECTOR2I(round((x+100)*1e6),round((y+60)*1e6))
                return any(z.GetNetname()=='GND' and z.IsOnLayer(layer) and
                           z.HitTestFilledArea(layer,point) for z in board.Zones())
            checked=0
            for t in tracks:
                if not t.net.startswith('USB_D_'):continue
                layer=pcbnew.In1_Cu if t.layer=='F.Cu' else pcbnew.In2_Cu
                for a,b in zip(t.pts,t.pts[1:]):
                    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
                    steps=max(1,math.ceil(length/.05))
                    for i in range(steps+1):
                        for offset in (-t.width/2,0,t.width/2):
                            x=a[0]+dx*i/steps-dy/length*offset
                            y=a[1]+dy*i/steps+dx/length*offset
                            # The signal-via antipad is unavoidable only at
                            # its own probe transition. Never exempt trunks.
                            if t.purpose.startswith('usb:fixture-') and any(
                                q.net==t.net and math.hypot(x-q.x,y-q.y)<=.51
                                for q in usb_vias):continue
                            checked+=1
                            self.assertTrue(covered(x,y,layer),
                                (key,t.purpose,x,y,'reference void'))
            self.assertGreater(checked,1800)
            for q in usb_vias:
                nearby=[g for g in ground if math.hypot(q.x-g.x,q.y-g.y)<=2]
                self.assertGreaterEqual(len(nearby),2)
                for g in nearby:
                    for layer in (pcbnew.In1_Cu,pcbnew.In2_Cu):
                        self.assertTrue(covered(g.x,g.y,layer),
                            (key,g.x,g.y,'return via missing filled plane'))
