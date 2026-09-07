# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from dataclasses import replace

from tools.bom import bom_rows
from tools.boardgen.design import PART_BY_REF


class BomTests(unittest.TestCase):
    def test_dnp_and_fitted_parts_never_merge(self):
        p = PART_BY_REF["R1"]
        rows = bom_rows([p, replace(p, ref="R99", dnp=True)])
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["Populate"] for r in rows}, {"yes", "no"})

    def test_fixture_pads_not_in_bom(self):
        self.assertEqual(bom_rows([PART_BY_REF["TP1"]]), [])
