# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A placement edit must invalidate fixed regulator-control copper."""
import unittest
from tools.boardgen.control import route_local_controls
from tools.boardgen.place import place
from tools.boardgen.variants import VARIANTS


class ControlPlacementTests(unittest.TestCase):
    def test_unreviewed_component_move_is_rejected(self):
        for variant in VARIANTS.values():
            for ref in ("U3", "R5", "R6"):
                placed = place(variant)
                next(p for p in placed if p.ref == ref).x += .1
                with self.subTest(variant=variant.key, ref=ref):
                    with self.assertRaisesRegex(ValueError, f"placement changed: {ref}"):
                        route_local_controls(placed)
