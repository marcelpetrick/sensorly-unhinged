"""Manufacturing cost estimate, computed from the actual design.

Joint counts, component counts and board areas come from the board model, so
this cannot drift away from what would actually be ordered. The *rates* are
researched inputs with sources recorded next to them - they are the part that
goes stale, and the part a real quote replaces.

    python -m tools.cost            # print the report
    python -m tools.cost --write    # write docs/60-manufacturing-cost.md

Everything here is a planning estimate. Nothing here is a quote.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .boardgen import geometry as G
from .boardgen.design import PARTS, PART_BY_REF
from .boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[1]
RESEARCHED = "2026-08-25"
USD_EUR = 0.92           # planning rate only
VAT_DE = 0.19            # German import VAT on goods + freight

# --------------------------------------------------------------------------
# Rates. Every line carries where it came from.
# --------------------------------------------------------------------------
RATES = {
    # JLCPCB Economic PCBA, jlcpcb.com/help/article/pcb-assembly-price
    "smt_setup_usd": (8.18, "JLCPCB Economic PCBA setup fee"),
    "stencil_usd": (1.53, "JLCPCB Economic PCBA stencil"),
    "smt_joint_usd": (0.0016, "JLCPCB SMT assembly, per joint"),
    "manual_joint_usd": (0.0164, "JLCPCB manual assembly, per joint"),
    "hand_solder_order_usd": (3.58, "JLCPCB hand-soldering labour, per order"),
    "extended_part_usd": (3.00, "JLCPCB fee per unique extended-library part"),
    # PCB fabrication, 4-layer FR-4, both boards are under 50 x 50 mm
    "fab_5pcs_usd": ((2.00, 9.00), "JLCPCB 4-layer, <50x50 mm, 5 pcs "
                     "(promotional floor to realistic with options)"),
    "fab_20pcs_usd": ((11.00, 32.00), "JLCPCB 4-layer, <50x50 mm, 20 pcs"),
    "freight_usd": ((14.00, 28.00), "JLCPCB express to Germany, small parcel"),
}

# Component prices, LCSC unless noted. Ranges are (low, high) in USD.
BOM_PRICES = {
    "U1": ((3.03, 3.92), "ESP32-C6-MINI-1-N4, LCSC C5736265: $3.92@1, "
           "$3.49@10, $3.24@30, $3.03@100"),
    "U2": ((4.00, 6.13), "SHT45-AD1F-R2, JLCPCB C5360602 (extended); "
           "DigiKey $6.13@1"),
    "U3": ((0.48, 1.10), "TPS62840DLCR, LCSC C2071859 from $0.48"),
    "U4": ((0.47, 1.20), "BQ24074RGTR, LCSC C54313 from $0.47"),
    "U5": ((0.08, 0.20), "USBLC6-2SC6, commodity ESD array"),
    "J1": ((0.08, 0.20), "HRO TYPE-C-31-M-12, commodity 16P receptacle"),
    "J2": ((0.12, 0.35), "JST S2B-PH-SM4-TB"),
    "L1": ((0.25, 0.55), "Murata DFE201612E-2R2M shielded inductor"),
    "SW1": ((0.12, 0.35), "SMD tactile switch"),
    "D1": ((0.01, 0.04), "0603 green LED"),
}
PASSIVE_USD = (0.008, 0.030)     # per 0402/0603/0805 1% part, LCSC basic

# Everything else in the finished unit. These are bought in Europe, so they are
# already in EUR and carry no import VAT line of their own.
EXTRAS_EUR = {
    "battery": ((4.00, 9.00), "protected 1S LiPo 500-1000 mAh, EU retail (EUR)"),
    "enclosure_self": ((0.60, 2.50), "3D printed in-house, material + failures"),
    "enclosure_service": ((8.00, 18.00), "printed by a service, two parts"),
    "labels_screws": ((0.30, 1.20), "QR label, insulator, fasteners"),
}

# Parts likely to be JLCPCB "extended" (feeder loading fee applies once each)
EXTENDED_REFS = {"U1", "U2", "U3", "U4", "J1", "J2", "L1", "SW1"}


@dataclass
class Design:
    smt_joints: int
    tht_joints: int
    components: int
    bom_lines: int
    passives: int
    extended: int
    area_a: float
    area_b: float


def measure() -> Design:
    smt = tht = comps = passives = 0
    for p in PARTS:
        if p.ref.startswith("TP") or p.exclude_from_bom:
            continue
        fp = G.get(p.footprint)
        n = sum(len(v) for v in fp.pads.values())
        n_tht = len(re.findall(r'\(pad "[^"]*" thru_hole ', fp.text))
        n_np = len(re.findall(r'\(pad "[^"]*" np_thru_hole ', fp.text))
        comps += 1
        tht += n_tht
        smt += n - n_tht - n_np
        if p.ref[0] in "RCL" and p.ref not in BOM_PRICES:
            passives += 1
    a, b = VARIANTS["a"], VARIANTS["b"]
    return Design(smt, tht, comps, len({p.value for p in PARTS
                                        if not p.exclude_from_bom}),
                  passives, len(EXTENDED_REFS),
                  a.width * a.height / 100.0, b.width * b.height / 100.0)


def bom_cost(d: Design) -> tuple[float, float]:
    lo = hi = 0.0
    for ref, ((l, h), _src) in BOM_PRICES.items():
        lo += l
        hi += h
    lo += d.passives * PASSIVE_USD[0]
    hi += d.passives * PASSIVE_USD[1]
    return lo, hi


def assembly_cost(d: Design, qty: int) -> tuple[float, float]:
    """Per-order assembly cost for `qty` boards of one variant."""
    r = {k: v[0] for k, v in RATES.items()}
    fixed = r["smt_setup_usd"] + r["stencil_usd"] \
        + d.extended * r["extended_part_usd"] + r["hand_solder_order_usd"]
    per_board = d.smt_joints * r["smt_joint_usd"] \
        + d.tht_joints * r["manual_joint_usd"]
    lo = fixed + qty * per_board
    # the high case assumes the setup/feeder side lands ~40 % worse
    hi = fixed * 1.4 + qty * per_board * 1.4
    return lo, hi


def scenario(d: Design, name: str, groups: list[tuple[str, int]],
             fab_key: str, enclosure: str) -> dict:
    parts_lo, parts_hi = bom_cost(d)
    total_units = sum(q for _v, q in groups)

    fab_lo, fab_hi = RATES[fab_key][0]
    fab = (fab_lo * len(groups), fab_hi * len(groups))

    asm_lo = asm_hi = 0.0
    for _variant, q in groups:
        a, b = assembly_cost(d, q)
        asm_lo += a
        asm_hi += b

    comp_lo = parts_lo * total_units
    comp_hi = parts_hi * total_units

    freight = RATES["freight_usd"][0]
    bat = EXTRAS_EUR["battery"][0]
    enc = EXTRAS_EUR[enclosure][0]
    misc = EXTRAS_EUR["labels_screws"][0]

    goods_lo = fab[0] + asm_lo + comp_lo
    goods_hi = fab[1] + asm_hi + comp_hi
    landed_lo = (goods_lo + freight[0]) * (1 + VAT_DE)
    landed_hi = (goods_hi + freight[1]) * (1 + VAT_DE)

    eu_lo = landed_lo * USD_EUR
    eu_hi = landed_hi * USD_EUR
    finish_lo = total_units * (bat[0] + enc[0] + misc[0])
    finish_hi = total_units * (bat[1] + enc[1] + misc[1])

    return dict(
        name=name, units=total_units,
        fab=fab, asm=(asm_lo, asm_hi), comps=(comp_lo, comp_hi),
        freight=freight, landed_pcba=(eu_lo, eu_hi),
        finishing=(finish_lo, finish_hi),
        total=(eu_lo + finish_lo, eu_hi + finish_hi),
        per_unit=((eu_lo + finish_lo) / total_units,
                  (eu_hi + finish_hi) / total_units),
    )


def eur(lo, hi, dp=0):
    f = f"{{:,.{dp}f}}"
    return f"€{f.format(lo)}–{f.format(hi)}"


def report() -> str:
    d = measure()
    protos = scenario(d, "Rev 1 prototypes — 5 × A + 5 × B",
                      [("a", 5), ("b", 5)], "fab_5pcs_usd", "enclosure_self")
    series = scenario(d, "Rev 2 series — 20 × the chosen variant",
                      [("b", 20)], "fab_20pcs_usd", "enclosure_self")

    o = [f"""# 60 — Manufacturing Cost Estimate (generated)

<!-- Generated by `make cost` from tools/cost.py. Do not edit: change the rate
     table, re-run, commit both. -->

**These are planning estimates, not quotes.** The quantities below come from the
real board model — joints, components and areas are counted from the generated
files — but every *rate* is a researched input that goes stale. A real quote
from the vendor's own uploader replaces this file, it does not agree with it.

Rates researched {RESEARCHED}. USD→EUR at {USD_EUR}. German import VAT
{VAT_DE:.0%} applied to goods + freight.

## What is actually being built

| | |
|---|---:|
| Components per board (excl. test pads) | {d.components} |
| SMT solder joints | {d.smt_joints} |
| Through-hole joints (USB-C shield lugs) | {d.tht_joints} |
| Distinct BOM lines | {d.bom_lines} |
| Passives (0402/0603/0805) | {d.passives} |
| Likely extended-library parts | {d.extended} |
| Variant A area | {d.area_a:.1f} cm² |
| Variant B area | {d.area_b:.1f} cm² |

Both boards fit inside 50 × 50 mm, which is the size band where 4-layer
fabrication is cheapest — that is not an accident of the floorplan.
"""]

    for s in (protos, series):
        o.append(f"""
## {s['name']}

| Line | | Cost |
|---|---|---:|
| PCB fabrication | USD, pre-VAT | ${s['fab'][0]:,.0f}–{s['fab'][1]:,.0f} |
| Assembly — setup, stencil, feeders, {d.smt_joints} joints × {s['units']} | USD, pre-VAT | ${s['asm'][0]:,.0f}–{s['asm'][1]:,.0f} |
| Components — {s['units']} × board BOM | USD, pre-VAT | ${s['comps'][0]:,.0f}–{s['comps'][1]:,.0f} |
| Freight to Germany | USD | ${s['freight'][0]:,.0f}–{s['freight'][1]:,.0f} |
| **Landed PCBA, incl. {VAT_DE:.0%} import VAT** | EUR | **{eur(*s['landed_pcba'])}** |
| Batteries, printed cases, labels — bought in the EU | EUR | {eur(*s['finishing'])} |
| **Total programme** | EUR | **{eur(*s['total'])}** |
| **Per finished unit** | EUR | **{eur(*s['per_unit'], dp=2)}** |
""")

    o.append(f"""
## Where the money goes

At these quantities the **components dominate**, and inside the components two
parts dominate: the ESP32-C6 module (${BOM_PRICES['U1'][0][0]:.2f}–{BOM_PRICES['U1'][0][1]:.2f})
and the SHT45-AD1F (${BOM_PRICES['U2'][0][0]:.2f}–{BOM_PRICES['U2'][0][1]:.2f}).
Together they are roughly two thirds of the bill of materials. Everything else —
charger, regulator, connectors, {d.passives} passives — is about a dollar and a half.

That has a direct consequence for the A/B decision: **variant B's extra 28 % of
board area is nearly free.** Fabrication is a small fraction of the total and
both boards sit in the same sub-50 mm price band. If B wins the thermal test, it
does not lose on cost.

The one lever that would move the number is the sensor. Dropping to SHT40-AD1B
saves roughly $1.50–2.50 per unit — about 8 % of the finished cost — at the price
of ±1.8 %RH instead of ±1.0 %RH and no filter membrane. That trade is open item
CS-1 and it should be decided on the Rev 1 humidity data, not on this table.

## Route comparison

| | China turnkey (JLCPCB-class) | EU (Aisler / Eurocircuits) |
|---|---|---|
| Boards + assembly | cheapest by a wide margin at these volumes | ~2–3× on the PCBA line |
| Lead time | 1–3 weeks incl. freight | days to ~1 week |
| VAT / customs | 19 % import VAT, paperwork, occasional delays | VAT handled domestically |
| Part sourcing | LCSC library, extended-part fees | you often supply or they source at distributor prices |
| When it wins | prototypes and small series like this one | when transit time, documentation or IPC class matter |

For 5 + 5 prototypes and a 20-unit series the China route is the obvious choice
on cost. The EU route becomes interesting the moment schedule matters more than
€200, or if the boards ever need IPC Class 2/3 documentation.

## What this estimate deliberately excludes

Engineering time. Test equipment and the reference hygrometer. The pogo fixture.
Failed prints and scrapped boards — budget one full spare set. Formal RED/EMC
testing, which is a five-figure line item and is why Rev 1 uses a pre-certified
module and stays a personal project.

## Sources

| Rate | Source |
|---|---|""")
    for _k, (_v, src) in RATES.items():
        o.append(f"| {_k} | {src} |")
    for ref, (_p, src) in BOM_PRICES.items():
        o.append(f"| {ref} | {src} |")
    for k, (_p, src) in EXTRAS_EUR.items():
        o.append(f"| {k} | {src} |")
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    text = report()
    if "--write" in sys.argv:
        (ROOT / "docs" / "60-manufacturing-cost.md").write_text(text)
        print("wrote docs/60-manufacturing-cost.md")
    else:
        print(text)
