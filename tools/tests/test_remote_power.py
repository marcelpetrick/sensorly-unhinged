# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Supply bridges must retain their reviewed physical source and terminals."""
import unittest
from unittest.mock import patch
from tools.boardgen import remote_power
from tools.boardgen.place import place
from tools.boardgen.route import Track, Via
from tools.boardgen.variants import VARIANTS


class RemotePowerGuards(unittest.TestCase):
    def inputs(self, key):
        return (VARIANTS[key], place(VARIANTS[key]),
                [Track('VBAT', .4, 'F.Cu', [(22.2, 10.25), (22.2, 13.2)])],
                [Via('VBAT', 19.2, 20.0)])

    def test_changed_endpoint_or_net_is_rejected(self):
        for key in ('a', 'b'):
            args = self.inputs(key)
            next(p for p in args[1] if p.ref == 'R14').x += .1
            with self.subTest(variant=key), self.assertRaisesRegex(ValueError, 'placement changed'):
                remote_power.route_remote_power(*args)
        changed = [p for p in remote_power.NETS['VBAT'] if p != ('R14', '1')]
        with patch.dict(remote_power.NETS, {'VBAT': changed}):
            with self.assertRaisesRegex(ValueError, 'no longer belongs'):
                remote_power.route_remote_power(*self.inputs('a'))

    def test_disconnected_or_changed_source_copper_is_rejected(self):
        for key in ('a', 'b'):
            v, placed, tracks, vias = self.inputs(key)
            with self.subTest(variant=key):
                with self.assertRaisesRegex(ValueError, 'source trunk changed'):
                    remote_power.route_remote_power(v, placed, [], vias)
                with self.assertRaisesRegex(ValueError, 'fixture via changed'):
                    remote_power.route_remote_power(v, placed, tracks, [])
                with self.assertRaisesRegex(ValueError, 'fixture via changed'):
                    remote_power.route_remote_power(v, placed, tracks, [Via('VBAT',19.2,20.0,.8,.3)])


class SystemPowerGuards(unittest.TestCase):
    def inputs(self, key):
        return (VARIANTS[key], place(VARIANTS[key]),
                [Track('VSYS', .4, 'F.Cu', [(28.2,10.75),(28.2,11.45)]),
                 Track('VSYS', .4, 'F.Cu', [(1.25,6.925),(2.95,6.925)])],
                [Via('VSYS',2.0,6.9)] if key=='b' else [])

    def test_changed_capacitor_or_net_is_rejected(self):
        for key in ('a','b'):
            args = self.inputs(key)
            next(p for p in args[1] if p.ref=='C10').x += .1
            with self.subTest(variant=key), self.assertRaisesRegex(ValueError,'placement changed'):
                remote_power.route_system_power(*args)
        changed=[p for p in remote_power.NETS['VSYS'] if p!=('C7','1')]
        with patch.dict(remote_power.NETS,{'VSYS':changed}):
            with self.assertRaisesRegex(ValueError,'no longer belongs'):
                remote_power.route_system_power(*self.inputs('a'))

    def test_missing_trunk_and_conflicting_via_are_rejected(self):
        for key in ('a','b'):
            v, placed, tracks, vias=self.inputs(key)
            with self.subTest(variant=key):
                with self.assertRaisesRegex(ValueError,'reviewed trunk'):
                    remote_power.route_system_power(v,placed,[],vias)
                with self.assertRaisesRegex(ValueError,'input via changed'):
                    remote_power.route_system_power(v,placed,tracks,[Via('GND',2.0,6.9)])
                with self.assertRaisesRegex(ValueError,'input via changed'):
                    remote_power.route_system_power(v,placed,tracks,[Via('VSYS',2.0,6.9,.8,.3)])

    def test_compact_system_fixture_drift_is_rejected(self):
        for reference in ('R5','TP3'):
            args=self.inputs('a')
            next(p for p in args[1] if p.ref==reference).x += .1
            with self.subTest(reference=reference), self.assertRaisesRegex(ValueError,'system-fixture placement changed'):
                remote_power.route_system_power(*args)
