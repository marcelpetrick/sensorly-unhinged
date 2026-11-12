# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn a kicad-cli DRC report into a build gate with an explicit policy.

kicad-cli's own --exit-code-violations counts unconnected nets as failures.
This development gate tracks incomplete routing explicitly in drc-budget.json.
It is not a manufacturing gate: tools.release_gate requires complete routing.

Policy:
  * any schematic/PCB parity difference -> fail (both come from one model)
  * any DRC violation at severity `error`  -> fail
  * unconnected items above the recorded budget -> fail
  * exact per-net open counts must match; an unchanged total cannot hide a regression
  * GND and USB-data airwires always fail, even if explicitly budgeted

Run: python -m tools.drc_gate _build/a/drc.json a
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET = ROOT / "hardware" / "drc-budget.json"

# Warnings we have looked at, understood and accepted. Each needs a reason.
ACCEPTED_WARNINGS = {
    "lib_footprint_mismatch":
        "U1 and U2 are the only two footprints carrying an embedded keep-out "
        "zone; their geometry is byte-identical to the library apart from "
        "position, reference, value, net and UUID (verified by diff). KiCad's "
        "parity check appears to trip on the embedded zone.",
    "isolated_copper":
        "Pour fragments on F.Cu/B.Cu that are not yet stitched, because the "
        "board is unrouted. In1.Cu carries the solid reference plane. Expected "
        "to clear as routing proceeds.",
    "silk_over_copper":
        "U4's pin-1 marker polygon clips an adjacent 0402 mask aperture. The "
        "marker is kept: assembly orientation of the charger matters more than "
        "a cosmetic silk clip, which the fab clips automatically.",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("a", "b"):
        print("usage: python -m tools.drc_gate REPORT.json a|b")
        return 1
    report_path, variant = Path(argv[0]), argv[1]
    try:
        d = json.loads(report_path.read_text())
        validate_report(d, variant)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"    INVALID DRC REPORT: {exc}")
        return 1
    try:
        budgets = json.loads(BUDGET.read_text())
        budget = budgets[variant]
        expected = budget["unconnected"]
        expected_nets = budget["unconnected_by_net"]
        if (type(expected) is not int or expected < 0 or not isinstance(expected_nets, dict)
                or any(not isinstance(net, str) or not net or type(count) is not int or count <= 0
                       for net, count in expected_nets.items())
                or sum(expected_nets.values()) != expected):
            raise ValueError("invalid or inconsistent per-net budget")
        actual_nets = unconnected_by_net(d)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"    INVALID ROUTING BUDGET/REPORT: {exc}")
        return 1

    parity = d["schematic_parity"]
    errors = [v for v in d["violations"] if v["severity"] == "error"]
    warnings = [v for v in d["violations"] if v["severity"] == "warning"]
    reviewed = budgets.get(variant, {}).get("warnings", [])
    allowance = Counter({(r["type"], tuple(sorted(r["items"]))): r["count"]
                         for r in reviewed})
    unexpected = []
    for w in warnings:
        key = warning_key(w)
        if w["type"] not in ACCEPTED_WARNINGS or allowance[key] <= 0:
            unexpected.append(w)
        else:
            allowance[key] -= 1
    unconnected = len(d["unconnected_items"])

    print(f"  variant {variant}: {len(errors)} errors, {len(warnings)} warnings "
          f"({len(unexpected)} unreviewed), {len(parity)} parity, "
          f"{unconnected} unconnected")

    bad = False
    for net in sorted(set(actual_nets) | set(expected_nets)):
        actual, expected_net = actual_nets[net], expected_nets.get(net, 0)
        if actual != expected_net:
            print(f"    OPEN COUNT {net}: expected {expected_net}, found {actual}; review and update per-net budget")
            bad = True
        if net in {"GND", "USB_D_P", "USB_D_N"} and (actual or expected_net):
            print(f"    PROHIBITED OPEN NET: {net}")
            bad = True
    # Schematic parity has to be exact. The board is generated from the same
    # model as the schematic, so any difference is a generator bug, not a
    # design choice.
    for v in parity:
        items = " / ".join(i.get("description", "") for i in v.get("items", []))
        print(f"    PARITY {v['type']}: {v.get('description')} | {items}")
        bad = True
    for v in errors:
        items = " / ".join(i.get("description", "") for i in v.get("items", []))
        print(f"    ERROR {v['type']}: {items}")
        bad = True
    for v in unexpected:
        items = " / ".join(i.get("description", "") for i in v.get("items", []))
        print(f"    UNREVIEWED WARNING {v['type']}: {items}")
        bad = True
    if expected is None:
        print(f"    no unconnected budget recorded for variant {variant}")
        bad = True
    elif unconnected > expected:
        print(f"    unconnected went UP: {expected} -> {unconnected}")
        bad = True
    elif unconnected < expected:
        print(f"    unconnected went DOWN: {expected} -> {unconnected}. "
              f"Good - record it in hardware/drc-budget.json.")
        bad = True
    return 1 if bad else 0


def unconnected_by_net(report):
    """KiCad JSON exposes net names in item descriptions, not separate fields.

    Require every endpoint to identify the same net. Reject unknown/localized
    formats rather than silently treating an unparsed connection as complete.
    """
    counts = Counter()
    for row in report["unconnected_items"]:
        if not isinstance(row, dict):
            raise ValueError("invalid unconnected item")
        items = row.get("items")
        if not isinstance(items, list) or len(items) < 2:
            raise ValueError("unconnected item has no endpoint pair")
        nets = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("invalid unconnected endpoint")
            names = re.findall(r"\[([^\[\]]+)\]", item.get("description", ""))
            if len(names) != 1:
                raise ValueError("unconnected endpoint has no unambiguous net name")
            nets.append(names[0])
        if len(set(nets)) != 1:
            raise ValueError("unconnected endpoints disagree on net")
        counts[nets[0]] += 1
    return counts


def warning_key(w):
    return w["type"], tuple(sorted(i["uuid"] for i in w["items"]))


def validate_report(d, variant):
    for key in ("violations", "unconnected_items", "schematic_parity",
                "included_severities", "ignored_checks"):
        if not isinstance(d.get(key), list):
            raise ValueError(f"missing or invalid {key}")
    if not {"error", "warning"} <= set(d["included_severities"]):
        raise ValueError("both error and warning checks are required")
    if d["ignored_checks"]:
        raise ValueError("ignored checks are not allowed")
    if Path(d.get("source", "")).name != f"env-sensor-{variant}.kicad_pcb":
        raise ValueError("report is for the wrong board")
    for violation in d["violations"]:
        if violation.get("severity") not in ("error", "warning"):
            raise ValueError("unrecognized severity")
        if not violation.get("type") or not isinstance(violation.get("items"), list):
            raise ValueError("invalid violation")
        if not violation["items"] or any(not i.get("uuid") for i in violation["items"]):
            raise ValueError("violation has no item identity")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
