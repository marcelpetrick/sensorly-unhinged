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

    def test_pack_ntc_drives_charger_ts(self):
        self.assertEqual(
            set(NETS["PACK_TS"]), {("U1", "6"), ("U4", "1"), ("J2", "2")})
        self.assertIn(("J2", "1"), NETS["GND"])

    def test_charging_defaults_disabled_until_temperature_is_valid(self):
        self.assertNotIn(("U4", "4"), NETS["GND"])
        self.assertEqual(
            set(NETS["CHARGE_EN_N"]), {("U4", "4"), ("Q1", "3"), ("R18", "1")})
        self.assertEqual(
            set(NETS["CHARGE_ENABLE"]), {("U1", "24"), ("Q1", "1"), ("R7", "1")})
        self.assertIn(("Q1", "2"), NETS["GND"])
        self.assertIn(("R7", "2"), NETS["GND"])
        self.assertIn(("R18", "2"), NETS["VBUS"])
        self.assertEqual(PART_BY_REF["R7"].value, "100k 1%")
        self.assertEqual(PART_BY_REF["R18"].value, "47k 1%")

    def test_usb_current_selection_fails_safe(self):
        self.assertIn(("U4", "5"), NETS["GND"])  # EN2 fixed low
        self.assertEqual(
            set(NETS["USB_ISEL"]), {("U1", "27"), ("U4", "6"), ("R8", "1")})
        self.assertIn(("R8", "2"), NETS["GND"])  # reset/Hi-Z => USB100

    def test_charge_and_ilim_resistors_are_pack_safe_at_tolerance(self):
        self.assertEqual(PART_BY_REF["R13"].value, "4k42 1%")
        self.assertEqual(PART_BY_REF["R11"].value, "8k00 1%")
        # BQ24074 datasheet maxima: KISET=975 Aohm, KILIM=1720 Aohm.
        self.assertLessEqual(975 / (4420 * 0.99), 0.225)
        self.assertLessEqual(1720 / (8000 * 0.99), 0.225)

    def test_active_low_led_current_path(self):
        self.assertIn(("R2", "1"), NETS["+3V0"])
        self.assertEqual(set(NETS["LED_A"]), {("R2", "2"), ("D1", "2")})
        self.assertEqual(set(NETS["LED_N"]), {("U1", "25"), ("D1", "1")})


if __name__ == "__main__":
    unittest.main()
