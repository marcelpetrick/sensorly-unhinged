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


def bom_rows():
    groups: dict[tuple, list[str]] = defaultdict(list)
    for p in PARTS:
        if p.exclude_from_bom:
            continue
        groups[(p.value, p.footprint.split(":")[-1], p.mpn, p.manufacturer,
                p.alt, p.desc)].append(p.ref)
    rows = []
    for (value, fp, mpn, mfr, alt, desc), refs in groups.items():
        refs.sort(key=lambda r: (r[0], int("".join(c for c in r if c.isdigit()) or 0)))
        rows.append({
            "Qty": len(refs),
            "Refs": ",".join(refs),
            "Value": value,
            "Footprint": fp,
            "MPN": mpn,
            "Manufacturer": mfr,
            "Second source": alt,
            "Notes": desc,
        })
    rows.sort(key=lambda r: (r["Refs"][0], -r["Qty"]))
    return rows


def main():
    out = ROOT / "hardware" / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    rows = bom_rows()
    with (out / "bom.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    with (out / "netlist.txt").open("w") as fh:
        fh.write("ENV sensor - flat netlist, generated from tools/boardgen/design.py\n")
        fh.write("Both variants share this netlist exactly.\n\n")
        for net in sorted(NETS):
            conns = ", ".join(f"{r}.{p}" for r, p in NETS[net])
            fh.write(f"{net}\n    {conns}\n\n")

    total = sum(r["Qty"] for r in rows)
    unique = len(rows)
    print(f"wrote hardware/outputs/bom.csv     {unique} lines, {total} placements")
    print(f"wrote hardware/outputs/netlist.txt {len(NETS)} nets")
    # AGENTS.md rule 6 applies to specified parts. A 0402 resistor given as
    # value + package + tolerance is multi-sourced by construction, so only
    # parts carrying an MPN need an explicit alternate.
    missing = [r["Refs"] for r in rows if r["MPN"] and not r["Second source"]]
    if missing:
        print("  AGENTS.md rule 6 - no second source recorded for:",
              ", ".join(missing))
    else:
        print("  every MPN-specified line has a qualified second source")


if __name__ == "__main__":
    main()
