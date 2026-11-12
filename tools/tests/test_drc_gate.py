# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools import drc_gate
from tools.drc_gate import validate_report, warning_key


class DrcTests(unittest.TestCase):
    def test_warning_count_cannot_exceed_reviewed_allowance(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            budget = directory / "budget.json"
            budget.write_text(json.dumps({"a": {"unconnected": 0, "unconnected_by_net": {}, "warnings": [
                {"type": "isolated_copper", "items": ["zone-1"], "count": 1}]}}))
            report = directory / "report.json"
            data = self.report()
            warning = dict(type="isolated_copper", severity="warning",
                           items=[dict(uuid="zone-1", description="test zone")])
            with patch.object(drc_gate, "BUDGET", budget), contextlib.redirect_stdout(io.StringIO()):
                for count, expected in ((1, 0), (2, 1)):
                    data["violations"] = [warning] * count
                    report.write_text(json.dumps(data))
                    self.assertEqual(drc_gate.main([str(report), "a"]), expected)

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


class NetBudgetTests(unittest.TestCase):
    def run_gate(self, nets, expected_nets, total=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = DrcTests().report()
            report["unconnected_items"] = [dict(items=[
                dict(description=f"Pad 1 [{net}] of U1", uuid="first"),
                dict(description=f"Via [{net}]", uuid="second")]) for net in nets]
            budget = {"a": {"unconnected": sum(expected_nets.values()) if total is None else total,
                            "unconnected_by_net": expected_nets, "warnings": []}}
            (root / "report.json").write_text(json.dumps(report))
            (root / "budget.json").write_text(json.dumps(budget))
            with patch.object(drc_gate, "BUDGET", root / "budget.json"), contextlib.redirect_stdout(io.StringIO()):
                return drc_gate.main([str(root / "report.json"), "a"])

    def test_same_total_cannot_hide_changed_net(self):
        self.assertEqual(self.run_gate(["EN", "VBUS"], {"EN": 1, "VBUS": 1}), 0)
        self.assertEqual(self.run_gate(["EN", "UART_RX"], {"EN": 1, "VBUS": 1}), 1)

    def test_ground_and_usb_opens_cannot_be_budgeted(self):
        for net in ("GND", "USB_D_P", "USB_D_N"):
            with self.subTest(net=net):
                self.assertEqual(self.run_gate([net], {net: 1}), 1)

    def test_inconsistent_budget_fails_closed(self):
        self.assertEqual(self.run_gate(["EN"], {"EN": 1}, total=2), 1)
        self.assertEqual(self.run_gate([], {"EN": True}), 1)

    def test_unidentified_or_mismatched_endpoint_fails_closed(self):
        for items in ([], [{"description": "Pad 1 [EN]"}],
                      [{"description": "Pad 1 [EN]"}, {"description": "Via"}],
                      [{"description": "Pad 1 [EN]"}, {"description": "Via [VBUS]"}]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                drc_gate.unconnected_by_net({"unconnected_items": [{"items": items}]})
