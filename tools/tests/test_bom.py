# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from dataclasses import replace

from tools.bom import bom_rows, sourcing_errors
from tools.boardgen.design import PART_BY_REF


class BomTests(unittest.TestCase):
    def test_dnp_and_fitted_parts_never_merge(self):
        p = PART_BY_REF["R1"]
        rows = bom_rows([p, replace(p, ref="R99", dnp=True)])
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["Populate"] for r in rows}, {"yes", "no"})

    def test_fixture_pads_not_in_bom(self):
        self.assertEqual(bom_rows([PART_BY_REF["TP1"]]), [])

    def test_fitted_generic_part_cannot_pass_sourcing_gate(self):
        generic = replace(PART_BY_REF["R1"], mpn="", manufacturer="")
        errors = sourcing_errors(bom_rows([generic]))
        self.assertIn("R1: missing MPN", errors)
        self.assertIn("R1: missing Manufacturer", errors)

    def test_fitted_single_source_needs_recorded_risk(self):
        unrecorded = replace(PART_BY_REF["R1"], alt=" ")
        self.assertEqual(sourcing_errors(bom_rows([unrecorded])),
                         ["R1: missing Second source"])

    def test_unpopulated_option_does_not_require_purchase_identity(self):
        dnp = replace(PART_BY_REF["R1"], dnp=True, mpn="", manufacturer="", alt="")
        self.assertEqual(sourcing_errors(bom_rows([dnp])), [])

    def test_current_fitted_bom_has_purchase_identity(self):
        self.assertEqual(sourcing_errors(bom_rows()), [])
