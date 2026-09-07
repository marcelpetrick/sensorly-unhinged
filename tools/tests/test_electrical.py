# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from tools.boardgen.design import NETS, PART_BY_REF


class ElectricalTests(unittest.TestCase):
    def test_baseline_has_rail_margin(self):
        self.assertEqual(PART_BY_REF["R6"].value, "267k 1%")

    def test_enable_link_can_be_removed(self):
        self.assertIn(("R5", "1"), NETS["VSYS"])
        self.assertEqual(set(NETS["EN_REG"]), {("U3", "4"), ("R5", "2")})
        self.assertNotIn(("U3", "4"), NETS["VSYS"])

    def test_charger_timers_not_disabled(self):
        self.assertFalse(any(("U4", "14") in pads for pads in NETS.values()))

    def test_active_low_led_current_path(self):
        self.assertIn(("R2", "1"), NETS["+3V0"])
        self.assertEqual(set(NETS["LED_A"]), {("R2", "2"), ("D1", "2")})
        self.assertEqual(set(NETS["LED_N"]), {("U1", "25"), ("D1", "1")})


if __name__ == "__main__":
    unittest.main()
