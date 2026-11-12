# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Guard the reviewed reset/fixture endpoints before searching new copper."""
from dataclasses import replace
import unittest
from unittest.mock import patch
from tools.boardgen.design import NETS
from tools.boardgen.fixture_branches import _check_endpoints
from tools.boardgen.place import place
from tools.boardgen.variants import VARIANTS


class FixtureEndpointGuards(unittest.TestCase):
    def test_each_reset_endpoint_move_requires_review(self):
        for variant in VARIANTS.values():
            placed = place(variant)
            _check_endpoints(placed)
            for ref in ('U1', 'TP6', 'R1', 'C4'):
                changed = [replace(p, x=p.x+.1) if p.ref==ref else p for p in placed]
                with self.subTest(variant=variant.key, ref=ref), self.assertRaisesRegex(ValueError, 'EN placement changed'):
                    _check_endpoints(changed)

    def test_each_reset_endpoint_net_change_requires_review(self):
        placed = place(VARIANTS['a'])
        for endpoint in NETS['EN']:
            changed = [pair for pair in NETS['EN'] if pair != endpoint]
            with self.subTest(endpoint=endpoint), patch.dict(NETS, EN=changed), self.assertRaisesRegex(ValueError, 'no longer belongs to EN'):
                _check_endpoints(placed)
