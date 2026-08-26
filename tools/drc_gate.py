# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn a kicad-cli DRC report into a build gate with an explicit policy.

kicad-cli's own --exit-code-violations counts unconnected nets as failures.
That is wrong for this repository *right now*: the boards are placement- and
rule-complete but only the four sensor-island nets are routed, so 80 unconnected
items is the expected state, not a regression.

Policy:
  * any schematic/PCB parity difference -> fail (both come from one model)
  * any DRC violation at severity `error`  -> fail
  * unconnected items above the recorded budget -> fail
  * unconnected items below the budget -> fail too, with "update the budget",
    so that routing progress is recorded rather than silently absorbed

Run: python -m tools.drc_gate _build/a/drc.json a
"""
from __future__ import annotations

import json
import sys
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
    report_path, variant = Path(argv[0]), argv[1]
    d = json.loads(report_path.read_text())
    budgets = json.loads(BUDGET.read_text()) if BUDGET.exists() else {}
    expected = budgets.get(variant, {}).get("unconnected")

    parity = d.get("schematic_parity") or []
    errors = [v for v in d["violations"] if v["severity"] == "error"]
    warnings = [v for v in d["violations"] if v["severity"] == "warning"]
    unexpected = [w for w in warnings if w["type"] not in ACCEPTED_WARNINGS]
    unconnected = len(d["unconnected_items"])

    print(f"  variant {variant}: {len(errors)} errors, {len(warnings)} warnings "
          f"({len(unexpected)} unreviewed), {len(parity)} parity, "
          f"{unconnected} unconnected")

    bad = False
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
