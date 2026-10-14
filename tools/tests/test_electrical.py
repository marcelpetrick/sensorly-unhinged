# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from tools.boardgen.design import NETS, PART_BY_REF
from tools.boardgen import geometry as G
from tools.boardgen.sch import emit


class ElectricalTests(unittest.TestCase):
    def test_power_package_land_patterns_follow_manufacturer_drawings(self):
        # Murata J(E)TE243A-0006D-01 p.5; TI 4219033/A land example.
        inductor = G.load(PART_BY_REF["L1"].footprint)
        self.assertEqual(inductor.pads["1"], [(-0.8, 0.0)])
        self.assertEqual(inductor.pads["2"], [(0.8, 0.0)])
        self.assertEqual(inductor.pad_size["1"], (0.8, 1.8))
        charger = G.load(PART_BY_REF["U4"].footprint)
        self.assertEqual(charger.pads["1"], [(-1.4, -0.75)])
        self.assertEqual(charger.pad_size["1"], (0.6, 0.25))
        for n in range(1, 17):
            w, h = charger.pad_size[str(n)]
            self.assertEqual(sorted((w, h)), [0.25, 0.6])
            x, y = charger.pads[str(n)][0]
            # Opposing perimeter/EP edges have 0.3 mm nominal clearance.
            gap = abs(x) - w / 2 - 0.8 if abs(x) > abs(y) else abs(y) - h / 2 - 0.8
            self.assertAlmostEqual(gap, 0.3)
        self.assertEqual(charger.pads["17"], [(0.0, 0.0)])
        self.assertEqual(charger.pad_size["17"], (1.6, 1.6))
        self.assertIn('(solder_paste_margin -0.065)', charger.text)
        esd = G.load(PART_BY_REF["U5"].footprint)
        for number in range(1, 7):
            self.assertEqual(esd.pad_size[str(number)], (1.2, 0.6))
            x, y = esd.pads[str(number)][0]
            self.assertEqual(abs(x), 1.15)
            self.assertIn(y, (-0.95, 0.0, 0.95))

    def test_baseline_has_rail_margin(self):
        self.assertEqual(PART_BY_REF["R6"].value, "267k 1%")

    def test_total_output_capacitance_has_conservative_upper_margin(self):
        # TPS62840 SLVSEC6D §7.3: effective COUT must not exceed 40 uF.
        # Selected Murata K-bin capacitors are ±10%; X5R/X7R allow ±15%.
        # Count every capacitor directly parallel with the output rail.
        import re
        rail = {ref for ref, pin in NETS["+3V0"] if ref.startswith("C")}
        ground = {ref for ref, pin in NETS["GND"] if ref.startswith("C")}
        total_uf = 0.0
        for ref in rail & ground:
            part = PART_BY_REF[ref]
            self.assertEqual(part.manufacturer, "Murata")
            self.assertEqual(part.mpn[13], "K")  # manufacturer ±10% bin
            nominal, unit = re.match(r"([\d.]+)([unp])F", part.value).groups()
            total_uf += float(nominal) * {"u": 1, "n": 0.001, "p": 0.000001}[unit]
        self.assertLessEqual(total_uf * 1.10 * 1.15, 40.0)
        # Espressif's entrance-cap recommendation is a nominal component value.
        c1_uf = float(PART_BY_REF["C1"].value.split("uF")[0])
        self.assertGreaterEqual(c1_uf, 10.0)

    def test_enable_link_can_be_removed(self):
        self.assertIn(("R5", "1"), NETS["VSYS"])
        self.assertEqual(set(NETS["EN_REG"]), {("U3", "4"), ("R5", "2")})
        self.assertNotIn(("U3", "4"), NETS["VSYS"])

    def test_charger_timers_not_disabled(self):
        self.assertFalse(any(("U4", "14") in pads for pads in NETS.values()))

    def test_pack_ntc_drives_charger_ts(self):
        self.assertEqual(
            set(NETS["PACK_TS"]), {("R21", "1"), ("U4", "1"), ("J2", "2")})
        self.assertIn(("J2", "1"), NETS["GND"])
        self.assertEqual(set(NETS["PACK_TS_SENSE"]), {("U1", "6"), ("R21", "2")})
        self.assertTrue(PART_BY_REF["R21"].dnp)

    def test_adc_isolation_link_is_dnp_in_generated_schematic(self):
        symbols = list(G._blocks(emit(), "symbol\n"))
        isolation = next(b for b in symbols if '(property "Reference" "R21"' in b)
        self.assertIn("(dnp yes)", isolation)

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
        self.assertNotIn(("U4", "5"), NETS["GND"])
        self.assertEqual(set(NETS["USB_EN2"]), {("U1", "19"), ("U4", "5"), ("R20", "1")})
        self.assertEqual(
            set(NETS["USB_ISEL"]), {("U1", "27"), ("U4", "6"), ("R8", "1")})
        self.assertIn(("R8", "2"), NETS["+3V0"])
        self.assertIn(("R20", "2"), NETS["+3V0"])  # valid rail + Hi-Z => standby

    def test_usb_nets_have_complementary_polarity_suffixes(self):
        self.assertIn(("U1", "18"), NETS["USB_D_P"])
        self.assertIn(("U1", "17"), NETS["USB_D_N"])
        self.assertNotIn("USB_DP", NETS)
        self.assertNotIn("USB_DM", NETS)

    def test_joint_download_strap_is_deterministic(self):
        self.assertEqual(set(NETS["BOOT_MODE_H"]), {("U1", "22"), ("R22", "1")})
        self.assertIn(("R22", "2"), NETS["+3V0"])
        self.assertEqual(PART_BY_REF["R22"].value, "10k 1%")
        self.assertEqual(PART_BY_REF["R22"].mpn, PART_BY_REF["R1"].mpn)

    def test_runtime_wake_is_separate_from_download_strap(self):
        self.assertEqual(set(NETS["BOOT_N"]), {("U1", "23"), ("TP7", "1")})
        self.assertEqual(set(NETS["BTN_PROV"]), {("U1", "13"), ("SW1", "1"), ("C5", "1"), ("R19", "1")})
        self.assertIn(("R19", "2"), NETS["+3V0"])

    def test_charge_and_ilim_resistors_are_pack_safe_at_tolerance(self):
        self.assertEqual(PART_BY_REF["R13"].value, "4k42 1%")
        self.assertEqual(PART_BY_REF["R11"].value, "8k06 1%")
        # BQ24074 datasheet maxima: KISET=975 Aohm, KILIM=1720 Aohm.
        self.assertLessEqual(975 / (4420 * 0.99), 0.225)
        self.assertLessEqual(1720 / (8060 * 0.99), 0.225)

    def test_active_low_led_current_path(self):
        self.assertIn(("R2", "1"), NETS["+3V0"])
        self.assertEqual(set(NETS["LED_A"]), {("R2", "2"), ("D1", "1")})
        self.assertEqual(set(NETS["LED_N"]), {("U1", "25"), ("D1", "2")})

    def test_led_numbering_matches_manufacturer_not_generic_library(self):
        # Kingbright DSAB0301 p.1 gives 1=A, 2=K; KiCad generic LED is opposite.
        from tools.boardgen.sch import LIB
        text = LIB.read_text()
        symbol = next(b for b in G._blocks(text, 'symbol "KP1608SGC"'))
        pin_blocks = list(G._blocks(symbol, 'pin '))
        anode = next(b for b in pin_blocks if '(name "A"' in b)
        cathode = next(b for b in pin_blocks if '(name "K"' in b)
        self.assertIn('(number "1"', anode)
        self.assertIn('(number "2"', cathode)
        footprint = G.load(PART_BY_REF["D1"].footprint)
        self.assertEqual(footprint.pads["1"], [(-0.825, 0.0)])
        self.assertEqual(footprint.pads["2"], [(0.825, 0.0)])
        self.assertEqual(footprint.pad_size["1"], (0.8, 0.8))


if __name__ == "__main__":
    unittest.main()
