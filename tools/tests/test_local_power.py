# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local switching-loop invariants survive malformed/chained escape attempts."""
import copy
import unittest
from unittest.mock import patch
from tools.boardgen.variants import POWER_LOCAL
from tools.boardgen.place import place
from tools.boardgen.power import route_local_power,validate_switch_routes
from tools.boardgen.route import Track,Via
from tools.boardgen.variants import VARIANT_A

class LocalPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.placed=place(VARIANT_A)
    def routes(self):
        return route_local_power(VARIANT_A,self.placed)
    def test_local_switch_path_is_accepted(self):
        tracks,vias=self.routes();validate_switch_routes(self.placed,tracks,vias)
    def test_chained_escape_is_rejected(self):
        tracks,vias=self.routes();tracks += [Track('SW_L',.15,'F.Cu',[(3.65,11.8),(3.65,12.8)],'switch-neckdown')]
        with self.assertRaisesRegex(ValueError,'only one'):validate_switch_routes(self.placed,tracks,vias)
    def test_overlong_escape_is_rejected(self):
        tracks,vias=self.routes();tracks[0].pts[-1]=(3.65,12)
        with self.assertRaisesRegex(ValueError,'invalid bounded'):validate_switch_routes(self.placed,tracks,vias)
    def test_arbitrary_remote_escape_is_rejected(self):
        tracks,vias=self.routes();tracks[0].pts=[(15,15),(15,16)]
        with self.assertRaisesRegex(ValueError,'start on U3.7'):validate_switch_routes(self.placed,tracks,vias)
    def test_escape_without_wide_trunk_is_rejected(self):
        tracks,vias=self.routes();tracks=[t for t in tracks if t.net!='SW_L' or t.width<.6]
        with self.assertRaisesRegex(ValueError,'terminate'):validate_switch_routes(self.placed,tracks,vias)
    def test_switch_layer_or_via_is_rejected(self):
        for layer in ('B.Cu','In1.Cu','In2.Cu'):
            tracks,vias=self.routes();tracks[1].layer=layer
            with self.subTest(layer=layer),self.assertRaisesRegex(ValueError,'F.Cu'):validate_switch_routes(self.placed,tracks,vias)
        tracks,vias=self.routes();vias.append(Via('SW_L',15,15))
        with self.assertRaisesRegex(ValueError,'without vias'):validate_switch_routes(self.placed,tracks,vias)
    def test_unreviewed_placement_change_is_rejected(self):
        changed=copy.deepcopy(self.placed);next(p for p in changed if p.ref=='C8').y+=.1
        with self.assertRaisesRegex(ValueError,'placement changed: C8'):route_local_power(VARIANT_A,changed)
    def test_live_placement_configuration_drift_is_rejected(self):
        with patch.dict(POWER_LOCAL,{'C7':(1.25,7.8,270)}):
            changed=place(VARIANT_A)
            with self.assertRaisesRegex(ValueError,'placement changed: C7'):
                route_local_power(VARIANT_A,changed)
