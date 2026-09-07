# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from tools.power_budget import budget


class PowerTests(unittest.TestCase):
    def test_sleep_only_charge_units(self):
        result = budget(500, .8, 90, 25, 0, 0)
        self.assertAlmostEqual(result["daily_mah"], .6)
        self.assertAlmostEqual(result["runtime_days"], 400/.6)

    def test_radio_scenario_misses_three_months(self):
        self.assertFalse(budget(500, .8, 90, 25, 2000, 160000)["target_feasible"])

    def test_impossible_sleep_budget(self):
        self.assertLess(budget(1, 1, 90, 25, 0, 0)["max_upload_uas"], 0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            budget(float("nan"), .8, 90, 25, 0, 0)
