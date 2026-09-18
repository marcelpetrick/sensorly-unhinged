# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A development DRC pass is not authorization to manufacture a product."""
import json
from pathlib import Path

from .drc_gate import validate_report

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"battery", "usb", "power", "mechanical", "assembly", "firmware", "instrument"}


def qualification_checks(root):
    manifest = json.loads((root / "hardware/release-readiness.json").read_text())
    checks = manifest["checks"]
    if (manifest["schema"] != 1 or {c["id"] for c in checks} != REQUIRED
            or len(checks) != len(REQUIRED)):
        raise ValueError("release checklist has missing or duplicate requirements")
    return checks


def evidence_path(root, check):
    evidence = check.get("evidence")
    path = root / evidence if isinstance(evidence, str) and evidence else None
    if (path is None or Path(evidence).is_absolute() or ".." in Path(evidence).parts
            or not path.resolve().is_relative_to(root.resolve())
            or not path.is_file() or not path.stat().st_size):
        raise ValueError(f"{check['id']}: missing qualification evidence ({check['owner']})")
    return path


def qualification_paths(root=ROOT):
    """Return reviewed evidence paths, or reject an incomplete manifest."""
    return [evidence_path(root, c) for c in qualification_checks(root)]


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
        for c in qualification_checks(root):
            try:
                evidence_path(root, c)
            except ValueError as exc:
                problems.append(str(exc))
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
