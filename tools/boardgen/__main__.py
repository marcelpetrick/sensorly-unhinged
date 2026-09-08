# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""CLI: python -m boardgen [--check-only]"""
from __future__ import annotations

import sys
from pathlib import Path

from .check import check
from .design import NETS
from .pcb import emit, write
from .place import place
from .project import write_all
from .render import render, write as write_svg
from .sch import write as write_sch
from .autoroute import route_rest
from .route import center_track_ends, route_island, stitch_ground
from .variants import VARIANTS
from .validate import validate

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    validate()
    check_only = "--check-only" in argv
    failed = False
    if not check_only:
        write_sch(ROOT)
        print("--- shared schematic")
        print("    wrote hardware/schematic/env-sensor.kicad_sch")
    for key, v in VARIANTS.items():
        placed = place(v)
        findings = check(v, placed)
        errors = [f for f in findings if f.severity == "ERROR"]
        print(f"--- variant {key.upper()}  {v.width} x {v.height} mm  ({v.revision})")
        for f in findings:
            print(f"    {f}")
        tracks, vias = route_island(v, placed, NETS)
        rest_t, rest_v, stats = route_rest(v, placed, tracks, vias)
        tracks = tracks + rest_t
        vias = vias + rest_v
        vias = vias + stitch_ground(v, placed, tracks, vias)
        tracks = center_track_ends(tracks, vias)
        total = sum(
            abs(t.pts[i + 1][0] - t.pts[i][0]) + abs(t.pts[i + 1][1] - t.pts[i][1])
            for t in tracks for i in range(len(t.pts) - 1))
        print(f"    routed: {len(tracks)} tracks, {total:.0f} mm, "
              f"{len(vias)} vias; {len(stats['failed'])} nets left for hand "
              f"routing")
        for f in stats["failed"]:
            print(f"      unrouted: {f}")
        if errors:
            failed = True
            continue
        if not check_only:
            out = ROOT / "hardware" / f"variant-{key}" / f"env-sensor-{key}.kicad_pcb"
            write(out, emit(v, placed, tracks, vias))
            write_all(ROOT, v)
            svg = ROOT / "docs" / "img" / f"floorplan-{key}.svg"
            write_svg(svg, render(v, placed, tracks, vias))
            print(f"    wrote {out.relative_to(ROOT)} (+ .kicad_pro, .kicad_dru, "
                  f"fp-lib-table) and {svg.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
