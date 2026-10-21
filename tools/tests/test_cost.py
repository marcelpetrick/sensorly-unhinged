# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Protect fitted costing and the distinction between material and billed area."""
import unittest
from dataclasses import replace
from unittest.mock import patch

from tools import cost


class CostTests(unittest.TestCase):
    def test_current_population_excludes_isolation_link(self):
        design = cost.measure()
        self.assertEqual((design.components, design.smt_joints, design.tht_joints), (46, 198, 4))
        self.assertEqual(design.bom_lines, 26)
        populated = [replace(p, dnp=False) if p.ref == "R21" else p for p in cost.PARTS]
        with patch.object(cost, "PARTS", populated):
            fitted = cost.measure()
            self.assertEqual((fitted.components, fitted.smt_joints), (47, 200))
            self.assertEqual(fitted.passives, design.passives + 1)
            actual_cost = cost.bom_cost(fitted)
        for original, fitted_cost, allowance in zip(cost.bom_cost(design), actual_cost, cost.PASSIVE_USD):
            self.assertAlmostEqual(fitted_cost - original, allowance)

    def test_priced_ic_dnp_excluded_from_cost_and_feeder_count(self):
        original = cost.measure()
        original_cost = cost.bom_cost(original)
        dnp = [replace(p, dnp=True) if p.ref == "U1" else p for p in cost.PARTS]
        with patch.object(cost, "PARTS", dnp):
            design = cost.measure()
            self.assertEqual(design.components, original.components - 1)
            self.assertEqual(design.extended, original.extended - 1)
            for before, after, price in zip(original_cost, cost.bom_cost(design), cost.BOM_PRICES["U1"][0]):
                self.assertAlmostEqual(before - after, price)

    def test_equal_values_do_not_merge_different_mpns(self):
        changed = [replace(p, mpn="ANOTHER-EXACT-10K-MPN") if p.ref == "R1" else p for p in cost.PARTS]
        with patch.object(cost, "PARTS", changed):
            self.assertEqual(cost.measure().bom_lines, 27)

    def test_irregular_outline_is_distinct_from_bounding_rectangle(self):
        design = cost.measure()
        self.assertAlmostEqual(design.material_area_a, 10.20)
        self.assertAlmostEqual(design.material_area_b, 12.10)
        self.assertAlmostEqual(design.area_b, 15.30)
        self.assertAlmostEqual(cost.material_area([(0, 0), (3, 0), (0, 4)]), 6.0)

    def test_panel_requires_setup_acceptance_and_independent_fab_allowance(self):
        args = (cost.measure(), "panel", [("a", 5), ("b", 5)], "fab_5pcs_usd", "enclosure_self")
        for supplied in ({}, {"panel_setup_shared": True}, {"panel_fab_usd": (100, 150)}):
            with self.subTest(supplied=supplied), self.assertRaises(ValueError):
                cost.scenario(*args, panelized=True, **supplied)
        panel = cost.scenario(*args, panelized=True, panel_setup_shared=True, panel_fab_usd=(100, 150))
        separate = cost.scenario(*args)
        self.assertEqual(panel["fab"], (100, 150))
        self.assertGreater(panel["total"][0], separate["total"][0])

    def test_missing_price_does_not_silently_omit_fitted_ic(self):
        extra = replace(cost.PARTS[0], ref="U99", mpn="NEW-IC")
        with patch.object(cost, "PARTS", cost.PARTS + [extra]), self.assertRaisesRegex(ValueError, "U99"):
            cost.bom_cost(cost.measure())
