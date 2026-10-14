# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Manufacturer internal conductors join only their documented pad groups."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.boardgen import geometry as G
from tools.boardgen.pcb import ORIGIN, emit, write
from tools.boardgen.place import place
from tools.boardgen.project import write_all
from tools.boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[2]


class ComponentJumperTests(unittest.TestCase):
    def report(self, ref, internal, short=False):
        variant = VARIANTS['a']
        part = next(p for p in place(variant) if p.ref == ref)
        with tempfile.TemporaryDirectory(prefix='sensorly-jumper-control-') as d:
            directory = Path(d)
            shutil.copytree(ROOT / 'hardware/lib', directory / 'hardware/lib')
            write_all(directory, variant)
            board = directory / 'hardware/variant-a/env-sensor-a.kicad_pcb'
            source = emit(variant, [part], [], [])
            if not internal:
                if ref == 'SW1':
                    source = source.replace('(duplicate_pad_numbers_are_jumpers yes)',
                                            '(duplicate_pad_numbers_are_jumpers no)')
                else:
                    for group in G._blocks(source, 'jumper_pad_groups'):
                        source = source.replace(group, '')
            if short:
                # Deliberately bridge unlike pins: these must remain different
                # nets despite the true conductors within each pad group.
                pins, net = (('1', '2'), 'BTN_PROV') if ref == 'SW1' else (('1', '3'), 'USB_D_N')
                points = []
                fp = G.get(part.footprint)
                for pin in pins:
                    x, y = G.xform(*fp.pads[pin][0], part.x, part.y, part.rot)
                    points.append((x + ORIGIN[0], y + ORIGIN[1]))
                (x1, y1), (x2, y2) = points
                segment = (f'(segment (start {x1} {y1}) (end {x2} {y2}) '
                           f'(width 0.15) (layer "F.Cu") (net "{net}") '
                           '(uuid "21264623-1354-4a6f-8573-ad249677449a"))')
                source = source.rstrip()[:-1] + segment + '\n)\n'
            write(board, source)
            report = directory / 'drc.json'
            # No zone refill: a copper pour could connect duplicate ground
            # terminals and invalidate the control's connectivity comparison.
            subprocess.run([os.environ.get('KICAD_CLI', 'kicad-cli'), 'pcb', 'drc',
                            '--format', 'json', '-o', str(report), str(board)],
                           check=True, capture_output=True, timeout=120)
            return json.loads(report.read_text())

    def test_internal_conductors_remove_only_documented_airwires(self):
        for ref in ('U5', 'SW1'):
            with self.subTest(ref=ref):
                baseline = self.report(ref, False)
                active = self.report(ref, True)
                self.assertEqual(len(baseline['unconnected_items']), 2)
                self.assertEqual(active['unconnected_items'], [])
                self.assertEqual([v for v in active['violations'] if v['severity'] == 'error'], [])

    def test_unlike_terminal_short_is_still_rejected(self):
        for ref in ('U5', 'SW1'):
            with self.subTest(ref=ref):
                report = self.report(ref, True, short=True)
                self.assertTrue(any(v['type'] == 'shorting_items' for v in report['violations']), report)
