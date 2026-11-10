# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Placement changes must invalidate the reviewed sense-divider trace."""
import unittest

from tools.boardgen.autoroute import route_rest
from tools.boardgen.place import place
from tools.boardgen.variants import VARIANTS


class SenseDividerPlacementTests(unittest.TestCase):
    def test_moved_sense_pad_rejects_fixed_trace(self):
        for key in ("a", "b"):
            for ref in ("R15", "C13"):
                placed = place(VARIANTS[key])
                next(part for part in placed if part.ref == ref).x += 0.1
                with self.subTest(variant=key, ref=ref):
                    with self.assertRaisesRegex(ValueError,
                                                f"VBAT_SENSE placement changed: {ref}.1"):
                        route_rest(VARIANTS[key], placed, [], [])
