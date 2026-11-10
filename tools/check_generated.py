# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject stale generated inputs before manufacturing qualification/export."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GENERATED_PATHS = (
    'hardware/schematic',
    'hardware/variant-a',
    'hardware/variant-b',
    'hardware/lib',
    'hardware/outputs/bom.csv',
    'hardware/outputs/netlist.txt',
    'docs/41-fixture-map.md',
    'docs/45-thermal-model.md',
    'docs/60-manufacturing-cost.md',
    'docs/61-cost-reduction.md',
    'docs/80-enclosure.md',
    'mechanical/env-sensor-case.scad',
    'mechanical/params-a.scad',
    'mechanical/params-b.scad',
    'mechanical/case-a.scad',
    'mechanical/case-b.scad',
    'docs/img/floorplan-a.svg',
    'docs/img/floorplan-b.svg',
)


def generated_status(root, paths):
    return subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
        cwd=root, check=True, capture_output=True, text=True).stdout


def check(root=ROOT, paths=GENERATED_PATHS):
    # Avoid replacing an engineer's uncommitted board/library edits.
    if generated_status(root, paths):
        raise ValueError("generated inputs have uncommitted changes; review and commit them before checking")
    subprocess.run(["make", "gen", "thermal", "bom", "cost", "mech"], cwd=root, check=True)
    drift = generated_status(root, paths)
    if drift:
        raise ValueError("generated inputs differ from committed source:\n" + drift)
    print("Generated inputs reproduce the committed files")


def main():
    try:
        check()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
