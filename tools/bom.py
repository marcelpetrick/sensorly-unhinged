# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""BOM and a human-readable netlist, straight from the shared design model.

The board files deliberately do not carry MPN fields (it trips KiCad's
library-parity check and duplicates data). The single source is design.py.

Run: python -m tools.bom
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .boardgen.design import NETS, PARTS

ROOT = Path(__file__).resolve().parents[1]


def bom_rows(parts=None):
    groups: dict[tuple, list[str]] = defaultdict(list)
    for p in PARTS if parts is None else parts:
        if p.exclude_from_bom:
            continue
        groups[(p.value, p.footprint.split(":")[-1], p.mpn, p.manufacturer,
                p.alt, p.desc, p.dnp)].append(p.ref)
    rows = []
    for (value, fp, mpn, mfr, alt, desc, dnp), refs in groups.items():
        refs.sort(key=lambda r: (r[0], int("".join(c for c in r if c.isdigit()) or 0)))
        rows.append({
            "Qty": len(refs),
            "Populate": "no" if dnp else "yes",
            "Refs": ",".join(refs),
            "Value": value,
            "Footprint": fp,
            "MPN": mpn,
            "Manufacturer": mfr,
            "Second source": alt,
            "Sourcing status": ("single-sourced, accepted risk for design exploration only; "
                                "alternate is unqualified, do not substitute" if mpn else
                                "generic specification; purchasing must qualify exact MPN"),
            "Notes": desc,
        })
    rows.sort(key=lambda r: (r["Refs"][0], -r["Qty"]))
    return rows


def sourcing_errors(rows):
    """Reject fitted lines that purchasing cannot identify or review."""
    return [f"{row['Refs']}: missing {field}" for row in rows
            if row["Populate"] == "yes"
            for field in ("MPN", "Manufacturer", "Second source")
            if not row[field].strip()]


def main():
    out = ROOT / "hardware" / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    rows = bom_rows()
    with (out / "bom.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    with (out / "netlist.txt").open("w") as fh:
        fh.write("ENV sensor - flat netlist, generated from tools/boardgen/design.py\n")
        fh.write("Both variants share this netlist exactly.\n\n")
        for net in sorted(NETS):
            conns = ", ".join(f"{r}.{p}" for r, p in NETS[net])
            fh.write(f"{net}\n    {conns}\n\n")

    total = sum(r["Qty"] for r in rows if r["Populate"] == "yes")
    unique = len(rows)
    print(f"wrote hardware/outputs/bom.csv     {unique} lines, {total} placements")
    print(f"wrote hardware/outputs/netlist.txt {len(NETS)} nets")
    missing = sourcing_errors(rows)
    if missing:
        print("  purchasing identity / AGENTS.md rule 6 failure:",
              "; ".join(missing))
    else:
        print("  alternate candidates recorded; NO substitute is qualified for assembly")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
