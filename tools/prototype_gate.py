# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prototype order review has different evidence from product qualification."""
import json
from .release_gate import ROOT, design_blockers, evidence_path

REQUIRED = {"electrical", "assembly", "procurement", "mechanical", "order"}


def checks(root=ROOT):
    manifest = json.loads((root / "hardware/prototype-readiness.json").read_text())
    rows = manifest["checks"]
    if (manifest["schema"] != 1 or manifest["purpose"] != "controlled-5-plus-5-engineering-prototypes"
            or len(rows) != len(REQUIRED) or {r["id"] for r in rows} != REQUIRED):
        raise ValueError("prototype checklist has missing, duplicate or invalid requirements")
    return rows


def review_paths(root=ROOT):
    return [evidence_path(root, row) for row in checks(root)]


def blockers(root=ROOT):
    problems = design_blockers(root)
    try:
        for row in checks(root):
            try:
                evidence_path(root, row)
            except ValueError as exc:
                problems.append(str(exc))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        problems.append(f"invalid prototype manifest: {exc}")
    return problems


def main():
    problems = blockers()
    for problem in problems:
        print(f"NOT PROTOTYPE-READY: {problem}")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
