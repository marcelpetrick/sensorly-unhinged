# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from tools.drc_gate import validate_report, warning_key


class DrcTests(unittest.TestCase):
    def report(self):
        return dict(violations=[], unconnected_items=[], schematic_parity=[],
                    included_severities=["error", "warning"], ignored_checks=[],
                    source="env-sensor-a.kicad_pcb")

    def test_complete_report(self):
        validate_report(self.report(), "a")

    def test_missing_parity_is_not_success(self):
        d = self.report()
        del d["schematic_parity"]
        with self.assertRaises(ValueError):
            validate_report(d, "a")

    def test_omitted_warnings_and_ignored_checks_fail(self):
        for field, value in (("included_severities", ["error"]),
                             ("ignored_checks", ["clearance"]),
                             ("source", "env-sensor-b.kicad_pcb")):
            d = self.report()
            d[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_report(d, "a")

    def test_warning_waivers_are_item_specific(self):
        a = dict(type="lib_footprint_mismatch", items=[dict(uuid="u1")])
        b = dict(type="lib_footprint_mismatch", items=[dict(uuid="u3")])
        self.assertNotEqual(warning_key(a), warning_key(b))
