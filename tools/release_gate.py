# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A development DRC pass is not authorization to manufacture a product."""
import json
from pathlib import Path

from .drc_gate import validate_report

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"battery", "usb", "power", "mechanical", "assembly", "firmware", "instrument"}


def blockers(root=ROOT):
    problems = []
    for variant in ("a", "b"):
        try:
            d = json.loads((root / f"_build/{variant}/drc.json").read_text())
            validate_report(d, variant)
            for key in ("violations", "unconnected_items", "schematic_parity"):
                if d[key]:
                    problems.append(f"{variant}: {len(d[key])} {key}")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            problems.append(f"{variant}: no valid DRC evidence: {exc}")
    try:
        manifest = json.loads((root / "hardware/release-readiness.json").read_text())
        checks = manifest["checks"]
        if manifest["schema"] != 1 or {c["id"] for c in checks} != REQUIRED or len(checks) != len(REQUIRED):
            raise ValueError("release checklist has missing or duplicate requirements")
        for c in checks:
            evidence = c.get("evidence")
            path = (root / evidence).resolve() if isinstance(evidence, str) and evidence else None
            if path is None or not path.is_relative_to(root.resolve()) or not path.is_file() or not path.stat().st_size:
                problems.append(f"{c['id']}: missing qualification evidence ({c['owner']})")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        problems.append(f"invalid readiness manifest: {exc}")
    return problems


def main():
    problems = blockers()
    for p in problems:
        print(f"NOT RELEASEABLE: {p}")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
