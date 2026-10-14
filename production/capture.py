# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Preserve a fixture console log and validate one engineering bring-up record.

This is not a production acceptance test. A failed record is retained as FAIL;
missing/malformed records are rejected without creating an apparent result.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def parse_log(raw: bytes) -> dict:
    records = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if not line.startswith('{'):
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError("Malformed JSON in console capture") from exc
        if isinstance(row, dict) and row.get("kind") == "sensorly-bringup":
            records.append(row)
    if len(records) != 1:
        raise ValueError(f"Expected exactly one bring-up record, found {len(records)}")
    row = records[0]
    if type(row.get("schema")) is not int or row["schema"] != 1:
        raise ValueError("Unsupported schema")
    for name, pattern in (("chip_id", r"[0-9a-f]{12}"), ("firmware_sha256", r"[0-9a-f]{64}")):
        if not isinstance(row.get(name), str) or not re.fullmatch(pattern, row[name]):
            raise ValueError(f"Invalid {name}")
    for name in ("factory_mode", "radio_started", "charge_enabled", "usb_present", "charging", "clock_valid"):
        if type(row.get(name)) is not bool:
            raise ValueError(f"Missing/invalid boolean {name}")
    if row.get("clock_valid") or row.get("acquired_at_utc", "missing") is not None:
        raise ValueError("Bring-up firmware must report an unset acquisition clock")
    for name in ("sensor_status", "adc_status"):
        if not isinstance(row.get(name), str) or not row[name]:
            raise ValueError(f"Missing {name}")
    for name, status, lower, upper in (("temperature_c", "sensor_status", -45, 130),
                                     ("humidity_rh", "sensor_status", 0, 100),
                                     ("battery_mv", "adc_status", 0, 6600)):
        val = row.get(name, "missing")
        if row[status] == "ESP_OK":
            if type(val) not in (int, float) or not math.isfinite(val) or not lower <= val <= upper:
                raise ValueError(f"Missing/invalid {name}")
        elif val is not None:
            raise ValueError(f"Failed acquisition must report null {name}")
    flags = row.get("quality_flags")
    if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
        raise ValueError("Missing quality flags")
    required = {"engineering_unqualified", "battery_meter_check_pending", "cooldown_unqualified"}
    if row["usb_present"]:
        required.add("usb_thermal_bias")
    if row["charging"]:
        required.add("unexpected_charge_status")
    if not required.issubset(flags):
        raise ValueError("Incomplete quality flags")
    if row.get("input_mode") != "STANDBY":
        raise ValueError("Unexpected input-current policy")
    return row


def assess(row: dict) -> list[str]:
    """Only observable firmware assertions, never electrical qualification."""
    faults = []
    for name in ("sensor_status", "adc_status"):
        if row[name] != "ESP_OK":
            faults.append(f"{name}: {row[name]}")
    if not row["factory_mode"]:
        faults.append("fixture TEST_MODE was not asserted")
    for name in ("radio_started", "charge_enabled", "charging"):
        if row[name]:
            faults.append(f"unexpected {name}")
    return faults


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="raw console capture; one boot")
    parser.add_argument("--serial", required=True, help="label, for example ENV-0001")
    parser.add_argument("--variant", choices=("a", "b"), required=True)
    parser.add_argument("--chip-id", required=True, help="12 lowercase hex digits from independent fixture inventory")
    parser.add_argument("--firmware-sha256", required=True, help="expected ELF SHA256 from the reviewed build")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"ENV-[0-9]{4,8}", args.serial) or not args.operator.strip():
        parser.error("Invalid serial or empty operator")
    try:
        raw = args.input.read_bytes()
        row = parse_log(raw)
        if row["chip_id"] != args.chip_id or row["firmware_sha256"] != args.firmware_sha256:
            raise ValueError("Device/image does not match independent fixture inventory")
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        faults = assess(row)
        record = {"schema": 1, "purpose": "engineering-bringup-only", "serial": args.serial,
                  "variant": args.variant, "hardware_revision": f"HW-{args.variant.upper()}1",
                  "operator": args.operator, "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                  "capture_tool_commit": commit, "capture_tool_dirty": dirty,
                  "console_sha256": hashlib.sha256(raw).hexdigest(),
                  "console_base64": base64.b64encode(raw).decode("ascii"),
                  "console_utf8": raw.decode("utf-8", errors="replace"),
                  "result": "FAIL" if faults else "BRINGUP_PASS", "faults": faults, "device": row}
        args.output_dir.mkdir(parents=True, exist_ok=True)
        # Exclusive creation: repeating a serial needs explicit operator disposition.
        destination = args.output_dir / f"{args.serial}.json"
        with destination.open("x") as output:
            json.dump(record, output, indent=2, allow_nan=False)
            output.write("\n")
        print(f"{record['result']}: {destination}; this is not production qualification")
        return 1 if faults else 0
    except (OSError, ValueError) as exc:
        print(f"Capture rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
