# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic console records test rejection paths; they are not device evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from production.capture import assess, main, parse_log


def record():
    return dict(schema=1, kind="sensorly-bringup", chip_id="001122334455",
                firmware_sha256="a" * 64, reset_reason=1, uptime_us=15000,
                acquired_at_utc=None, clock_valid=False, factory_mode=True,
                radio_started=False, charge_enabled=False, input_mode="USB100",
                usb_present=True, charging=False, sensor_status="ESP_OK", adc_status="ESP_OK",
                temperature_c=21.5, humidity_rh=48.2, battery_mv=3800,
                quality_flags=["engineering_unqualified", "battery_meter_check_pending",
                               "cooldown_unqualified", "usb_thermal_bias"])


class CaptureTests(unittest.TestCase):
    def wire(self, row):
        return ("boot log\n" + json.dumps(row) + "\n").encode()

    def test_good_record_is_only_bringup(self):
        row = parse_log(self.wire(record()))
        self.assertEqual(assess(row), [])
        self.assertIn("engineering_unqualified", row["quality_flags"])

    def test_missing_duplicate_and_malformed_are_rejected(self):
        for raw in (b"boot only", self.wire(record()) * 2, b'{broken'):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                parse_log(raw)

    def test_invalid_types_missing_fields_and_nonfinite_are_rejected(self):
        for key, bad in (("factory_mode", "true"), ("battery_mv", True),
                         ("temperature_c", float('nan')), ("humidity_rh", 101),
                         ("input_mode", "USB500"), ("chip_id", "bad"),
                         ("firmware_sha256", "a"), ("quality_flags", [])):
            row = record(); row[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_log(self.wire(row))
        row = record(); del row["battery_mv"]
        with self.assertRaises(ValueError):
            parse_log(self.wire(row))

    def test_crc_failure_is_preserved_and_fails_assessment(self):
        row = record()
        row.update(sensor_status="ESP_ERR_INVALID_CRC", temperature_c=None, humidity_rh=None)
        self.assertTrue(assess(parse_log(self.wire(row))))
        row["temperature_c"] = 0  # masking sensor failure with zero is rejected
        with self.assertRaises(ValueError): parse_log(self.wire(row))

    def test_unsafe_states_cannot_pass(self):
        for key in ("charge_enabled", "radio_started", "charging", "factory_mode"):
            row = record(); row[key] = key != "factory_mode"
            if key == "charging": row["quality_flags"].append("unexpected_charge_status")
            self.assertTrue(assess(parse_log(self.wire(row))))

    def test_identity_mismatch_rejects_and_retest_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "console.log"; source.write_bytes(self.wire(record()))
            output = Path(d) / "records"
            args = ["--input", str(source), "--serial", "ENV-0001", "--variant", "a",
                    "--operator", "synthetic-test", "--output-dir", str(output),
                    "--firmware-sha256", "a" * 64, "--chip-id", "001122334456"]
            self.assertEqual(main(args), 2)
            self.assertFalse(output.exists())
            args[-1] = "001122334455"
            self.assertEqual(main(args), 0)
            saved = (output / "ENV-0001.json").read_bytes()
            self.assertEqual(main(args), 2)
            self.assertEqual((output / "ENV-0001.json").read_bytes(), saved)
            result = json.loads(saved)
            self.assertEqual(result["purpose"], "engineering-bringup-only")
            self.assertEqual(result["result"], "BRINGUP_PASS")

    def test_failed_result_is_retained(self):
        with tempfile.TemporaryDirectory() as d:
            row = record(); row["factory_mode"] = False
            source = Path(d) / "console.log"; source.write_bytes(self.wire(row))
            args = ["--input", str(source), "--serial", "ENV-0002", "--variant", "b",
                    "--operator", "synthetic-test", "--output-dir", d,
                    "--firmware-sha256", "a" * 64, "--chip-id", row["chip_id"]]
            self.assertEqual(main(args), 1)
            self.assertEqual(json.loads((Path(d) / "ENV-0002.json").read_text())["result"], "FAIL")
