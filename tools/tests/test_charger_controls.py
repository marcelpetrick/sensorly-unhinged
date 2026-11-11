# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reviewed charger endpoints fail closed on placement or net changes."""
import unittest
from unittest.mock import patch
from tools.boardgen import charger_control
from tools.boardgen.place import place
from tools.boardgen.variants import VARIANTS


class ChargerControlGuards(unittest.TestCase):
    def test_changed_endpoint_position_requires_review(self):
        for ref in ('U4', 'J2'):
            with self.subTest(ref=ref):
                placed = place(VARIANTS['b'])
                next(p for p in placed if p.ref == ref).x += .1
                with self.assertRaises(ValueError):
                    charger_control.route_charger_controls(VARIANTS['b'], placed)

    def test_changed_endpoint_net_requires_review(self):
        placed = place(VARIANTS['b'])
        original = charger_control.NETS['PACK_TS']
        for endpoint in (('U4', '1'), ('J2', '2')):
            with self.subTest(endpoint=endpoint), patch.dict(charger_control.NETS,
                    {'PACK_TS': [p for p in original if p != endpoint]}):
                with self.assertRaisesRegex(ValueError, 'must remain PACK_TS'):
                    charger_control.route_charger_controls(VARIANTS['b'], placed)

    def test_changed_enable_endpoint_requires_review(self):
        for ref, number, net in (('Q1', '3', 'CHARGE_EN_N'), ('R18', '1', 'CHARGE_EN_N'),
                                 ('Q1', '1', 'CHARGE_ENABLE'), ('R7', '1', 'CHARGE_ENABLE')):
            placed = place(VARIANTS['a'])
            next(p for p in placed if p.ref == ref).x += .1
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                charger_control.route_charger_controls(VARIANTS['a'], placed)
            original = charger_control.NETS[net]
            with self.subTest(ref=ref, net=True), patch.dict(charger_control.NETS,
                    {net: [p for p in original if p != (ref, number)]}):
                with self.assertRaisesRegex(ValueError, 'must remain ' + net):
                    charger_control.route_charger_controls(VARIANTS['a'], place(VARIANTS['a']))

    def test_changed_status_endpoint_requires_review(self):
        for key, ref, number in (('a', 'R10', '2'), ('a', 'U4', '9'),
                                 ('b', 'R10', '2'), ('b', 'TP14', '1')):
            placed = place(VARIANTS[key])
            next(p for p in placed if p.ref == ref).x += .1
            with self.subTest(variant=key, ref=ref), self.assertRaises(ValueError):
                charger_control.route_charger_controls(VARIANTS[key], placed)
            original = charger_control.NETS['CHG_N']
            with self.subTest(variant=key, ref=ref, net=True), patch.dict(charger_control.NETS,
                    {'CHG_N': [p for p in original if p != (ref, number)]}):
                with self.assertRaisesRegex(ValueError, 'must remain CHG_N'):
                    charger_control.route_charger_controls(VARIANTS[key], place(VARIANTS[key]))
