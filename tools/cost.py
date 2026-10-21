# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Historical manufacturing-cost illustration with current design quantities.

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
from .boardgen.design import PARTS
from .boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[1]
RESEARCHED = "2026-09-09"
USD_EUR = 0.92           # historical planning conversion, not current FX
VAT_DE = 0.19            # historical arithmetic assumption; excludes duty/clearance

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
    # Historical sub-50 mm fabrication allowances; NOT quotes for current B (51 mm).
    "fab_5pcs_usd": ((2.00, 9.00), "JLCPCB 4-layer, <50x50 mm, 5 pcs "
                     "(historical allowance; not a quote for this design)"),
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
    "Q1": ((0.02, 0.20), "onsemi 2N7002LT1G; DigiKey/Mouser planning range, "
           "checked 2026-09-09"),
    "J1": ((0.08, 0.20), "HRO TYPE-C-31-M-12, commodity 16P receptacle"),
    "J2": ((0.50, 0.60), "Molex 53261-0371; Mouser Germany EUR 0.542@1 / "
           "0.464@10 on 2026-09-09, converted with the report planning rate"),
    "L1": ((0.25, 0.55), "historical Murata DFE201612E family allowance; exact =P2 quote TBC"),
    "SW1": ((0.12, 0.35), "SMD tactile switch"),
    "D1": ((0.01, 0.04), "0603 green LED"),
}
PASSIVE_USD = (0.008, 0.030)     # per 0402/0603/0805 1% part, LCSC basic

# Cost-down candidates: ref -> (new price range, what it is, what it costs you)
SWAPS = {
    "sensor": ("U2", (1.20, 2.50), "SHT40-AD1B",
               "+-0.2 C / +-1.8 %RH instead of +-0.1 / +-1.0, and no polyimide "
               "membrane. Same footprint, same address, same driver."),
    "sensor_mid": ("U2", (2.40, 4.20), "SHT40-AD1F",
                   "keeps the filter membrane, drops only the accuracy bin. "
                   "Same footprint, same address, same driver."),
    "mcu": ("U1", (1.40, 2.20), "ESP32-C3-MINI-1-N4",
            "loses 802.15.4 (Thread/Zigbee/Matter) and Wi-Fi 6 TWT. Same "
            "module outline and land pattern, but a different pin map - a "
            "netlist, board and firmware redesign; unqualified candidate."),
    "charger": ("U4", (0.20, 0.45), "MCP73831",
                "loses the power path, so the load hangs off the cell while "
                "charging, and loses the NTC input. Different footprint."),
}

# Everything else in the finished unit. These are bought in Europe, so they are
# already in EUR and carry no import VAT line of their own.
EXTRAS_EUR = {
    "battery": ((4.00, 9.00), "provisional generic-pack allowance only; "
                "LP702040 FD_3245_20 supplier quote is TBC (EUR)"),
    "enclosure_self": ((0.60, 2.50), "3D printed in-house, material + failures"),
    "enclosure_service": ((8.00, 18.00), "printed by a service, two parts"),
    "labels_screws": ((0.30, 1.20), "QR label, insulator, fasteners"),
}

# Parts likely to be JLCPCB "extended" (feeder loading fee applies once each)
EXTENDED_REFS = {"U1", "U2", "U3", "U4", "Q1", "J1", "J2", "L1", "SW1"}


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
    material_area_a: float
    material_area_b: float


def fitted_parts():
    """The same population excluded from BOM/CPL exports, including DNP."""
    return [p for p in PARTS if not p.dnp and not p.exclude_from_bom
            and not p.ref.startswith("TP")]


def material_area(outline):
    """Shoelace polygon area, mm²; independent of the fab billing rectangle."""
    pairs = zip(outline, outline[1:] + outline[:1])
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in pairs)) / 2


def measure() -> Design:
    smt = tht = passives = 0
    fitted = fitted_parts()
    for p in fitted:
        fp = G.get(p.footprint)
        n = sum(len(v) for v in fp.pads.values())
        n_tht = len(re.findall(r'\(pad "[^"]*" thru_hole ', fp.text))
        n_np = len(re.findall(r'\(pad "[^"]*" np_thru_hole ', fp.text))
        tht += n_tht
        smt += n - n_tht - n_np
        if p.ref[0] in "RCL" and p.ref not in BOM_PRICES:
            passives += 1
    a, b = VARIANTS["a"], VARIANTS["b"]
    return Design(smt, tht, len(fitted), len({p.mpn for p in fitted}),
                  passives, len(EXTENDED_REFS & {p.ref for p in fitted}),
                  a.width * a.height / 100.0, b.width * b.height / 100.0,
                  material_area(a.outline) / 100.0, material_area(b.outline) / 100.0)


def bom_cost(d: Design, swaps: tuple[str, ...] = ()) -> tuple[float, float]:
    replaced = {SWAPS[k][0]: SWAPS[k][1] for k in swaps}
    lo = hi = 0.0
    for part in fitted_parts():
        if part.ref in BOM_PRICES:
            l, h = replaced.get(part.ref, BOM_PRICES[part.ref][0])
        elif part.ref[0] in "RCL":
            l, h = PASSIVE_USD
        else:
            raise ValueError(f"No historical price allowance for fitted {part.ref}")
        lo += l
        hi += h
    return lo, hi


PANEL_FEE_USD = 8.21             # JLCPCB, panelized design > 1


def assembly_cost(d: Design, qty: int, *, extended: int | None = None,
                  hand_solder: bool = True) -> tuple[float, float]:
    """Per-order assembly cost for `qty` boards sharing one setup."""
    r = {k: v[0] for k, v in RATES.items()}
    ext = d.extended if extended is None else extended
    fixed = r["smt_setup_usd"] + r["stencil_usd"] + ext * r["extended_part_usd"]
    per_board = d.smt_joints * r["smt_joint_usd"]
    if hand_solder:
        fixed += r["hand_solder_order_usd"]
        per_board += d.tht_joints * r["manual_joint_usd"]
    lo = fixed + qty * per_board
    # the high case assumes the setup/feeder side lands ~40 % worse
    hi = fixed * 1.4 + qty * per_board * 1.4
    return lo, hi


def scenario(d: Design, name: str, groups: list[tuple[str, int]],
             fab_key: str, enclosure: str, *, panelized: bool = False,
             swaps: tuple[str, ...] = (), extended: int | None = None,
             hand_solder: bool = True, panel_setup_shared: bool = False,
             panel_fab_usd: tuple[float, float] | None = None) -> dict:
    parts_lo, parts_hi = bom_cost(d, swaps)
    total_units = sum(q for _v, q in groups)

    fab_lo, fab_hi = RATES[fab_key][0]
    fab = (fab_lo * len(groups), fab_hi * len(groups))

    if panelized:
        # Shared BOM does not establish vendor acceptance, setup sharing or
        # panel fabrication price. Callers must explicitly supply both.
        if not panel_setup_shared or panel_fab_usd is None:
            raise ValueError("panel scenario needs accepted shared setup and a panel fabrication allowance")
        asm_lo, asm_hi = assembly_cost(d, total_units, extended=extended,
                                       hand_solder=hand_solder)
        asm_lo += PANEL_FEE_USD
        asm_hi += PANEL_FEE_USD
        fab = panel_fab_usd
    else:
        asm_lo = asm_hi = 0.0
        for _variant, q in groups:
            a, b = assembly_cost(d, q, extended=extended,
                                 hand_solder=hand_solder)
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
    a, b = VARIANTS["a"], VARIANTS["b"]
    protos = scenario(d, "Historical 5 × A + 5 × B illustration",
                      [("a", 5), ("b", 5)], "fab_5pcs_usd", "enclosure_self")
    series = scenario(d, "Historical 20 × chosen variant illustration",
                      [("b", 20)], "fab_20pcs_usd", "enclosure_self")
    o = [f"""# 60 — Historical Manufacturing Cost Illustration (generated)

<!-- Generated by `make cost` from tools/cost.py. Do not edit: change the model,
     re-run, commit both. -->

**Historical arithmetic only: these are not current quotes or delivered-price
bounds.** Rates are retained from {RESEARCHED}, using the old planning conversion
USD→EUR {USD_EUR} and a {VAT_DE:.0%} VAT arithmetic assumption. They have not been
revalidated for the current footprint/BOM or current taxes. The
[15 October manufacturer review](../manufacturer_review20261015.md) supersedes
this document for supplier selection and explains current quote requirements.
No order or release is authorized by this report.

## Current fitted design, counted from the shared model

| Quantity per board | Count |
|---|---:|
| Fitted components, excluding test pads and DNP | {d.components} |
| Fitted SMT package joints | {d.smt_joints} |
| Fitted through-hole joints (USB shield) | {d.tht_joints} |
| Unique fitted MPNs | {d.bom_lines} |
| Passives using a generic historical price allowance | {d.passives} |
| Assumed chargeable Extended types (unverified) | {d.extended} |
| A bounding rectangle | {a.width:.0f} × {a.height:.0f} mm / {d.area_a:.2f} cm² |
| B bounding rectangle | {b.width:.0f} × {b.height:.0f} mm / {d.area_b:.2f} cm² |
| A actual outline material | {d.material_area_a:.2f} cm² |
| B actual outline material | {d.material_area_b:.2f} cm² |

R21 is DNP and contributes neither a placement, joints nor component cost.
Distinct MPNs are counted independently of equal value labels. The Extended
count is a historical assumption, not a checked assembly-library classification.

B has {(d.material_area_b / d.material_area_a - 1) * 100:.1f}% more actual material,
but {(d.area_b / d.area_a - 1) * 100:.1f}% more bounding-rectangle area than A.
**B exceeds 50 mm in one dimension.** Neither material area nor a shared BOM
establishes a fab price band; irregular routing, rails, finish and the accepted
stackup must be quoted. The old sub-50 mm fab allowances below are retained only
to expose the historical calculation and are not applicable quotes for B.
"""]
    for row in (protos, series):
        o.append(f"""
## {row['name']}

These totals assume one combined shipment, separate setup for each layout,
{d.extended} chargeable Extended types, generic passive prices and zero customs
duty/clearance charges. Their low/high columns vary old inputs, not all unknowns.

| Historical allowance | Currency | Range |
|---|---|---:|
| Bare fabrication (unverified size/options) | USD | ${row['fab'][0]:.0f}–{row['fab'][1]:.0f} |
| Assembly setup, stencil, feeders and joints | USD | ${row['asm'][0]:.0f}–{row['asm'][1]:.0f} |
| Fitted components | USD | ${row['comps'][0]:.0f}–{row['comps'][1]:.0f} |
| Freight | USD | ${row['freight'][0]:.0f}–{row['freight'][1]:.0f} |
| PCBA arithmetic with assumed 19% VAT, before duty/clearance | EUR | {eur(*row['landed_pcba'])} |
| Pack, in-house case and miscellaneous allowances | EUR | {eur(*row['finishing'])} |
| Partial project arithmetic | EUR | {eur(*row['total'])} |
| Partial arithmetic per unit | EUR | {eur(*row['per_unit'], dp=2)} |
""")
    o.append("""
## Missing quote inputs and vendor comparison

Obtain dated exact-MPN availability, minimum purchases, attrition and surplus
terms, actual stackup, array/depanelization acceptance, inspection, firmware and
functional-test scope, rework terms and freight/Incoterms. The pack/NTC/harness,
case service, fixture, reference instruments, engineering, failed units and
formal qualification are not fully priced. Generic allowances do not qualify
any alternate component. This is not an all-in landed or finished-product cost.

There is no demonstrated China/EU price or schedule ranking. Compare accepted
quotations for the same deliverable, including recoverable VAT where applicable;
see the manufacturer review for process eligibility and import-cost treatment.

## Historical input record

JLC assembly fee source: https://jlcpcb.com/help/article/pcb-assembly-price .
The source links and exact supplier questions were revisited in the October
manufacturer review; the values below deliberately preserve the September model.

| Input | Historical source or assumption |
|---|---|""")
    for key, (_value, source) in RATES.items():
        o.append(f"| {key} | {source} |")
    for ref, (_price, source) in BOM_PRICES.items():
        o.append(f"| {ref} | {source} |")
    for key, (_price, source) in EXTRAS_EUR.items():
        o.append(f"| {key} | {source} |")
    return "\n".join(o) + "\n"


def reduction_report() -> str:
    d = measure()
    one_job = assembly_cost(d, 5)
    both_jobs = tuple(2 * v for v in one_job)
    shared_job = tuple(v + PANEL_FEE_USD for v in assembly_cost(d, 10))
    saving = tuple(a - b for a, b in zip(both_jobs, shared_job))
    return f"""# 61 — Historical Cost-Reduction Sensitivities (generated)

<!-- Generated by `make cost` from tools/cost.py. Do not edit. -->

**Historical {RESEARCHED} input model, not quotations or vendor recommendations.**
[The manufacturer review](../manufacturer_review20261015.md) supersedes this
report for purchasing. [The cost illustration](60-manufacturing-cost.md) records
current fitted counts and the limitations of the old rates.

## Pool purchasing and shipping before assuming shared assembly setup

One procurement pool and one parcel may avoid duplicate handling while keeping
two fabrication/placement jobs. A and B share {d.bom_lines} fitted MPNs, but have
separate placement files and different sensor-bypass capacitor C6 rotations.
A shared electrical BOM
therefore does not establish one stencil, one setup or vendor panel acceptance.
AISLER excludes standard mixed-design panels; other vendors impose eligibility,
size, spacing or job-charge conditions. See the dated manufacturer review.

The following **assembly-only conditional arithmetic** assumes acceptance of one
shared setup and all historical fee inputs, including {d.extended} chargeable
Extended types. It excludes the panel fabrication price and every additional
engineering/support/depanelization/inspection charge.

| Historical assembly scenario, 5 A + 5 B | USD |
|---|---:|
| Two independent setup/stencil/feeder jobs | ${both_jobs[0]:.2f}–{both_jobs[1]:.2f} |
| One accepted shared job plus historical ${PANEL_FEE_USD:.2f} panel fee | ${shared_job[0]:.2f}–{shared_job[1]:.2f} |
| Conditional avoided assembly fees | ${saving[0]:.2f}–{saving[1]:.2f} |

This is not a project saving. Subtract extra panel fabrication, engineering,
handling, inspection and transport costs first; the result may be negative.
No panel total is calculated without an explicit panel fabrication allowance
and accepted setup sharing. Actual fees and Economic/Standard eligibility need
fresh quotations. Tabs/supports must avoid the B neck, sensor island and antenna
strip, and depanelization must be reviewed with the assembler.

## Changes that require engineering qualification

An all-SMD USB connector, different library passives, another sensor bin, another
MCU or another charger are **unqualified redesign candidates**, not discounts on
the fitted BOM. Recheck footprints, pin maps, capacitor behavior, mechanical
retention, firmware and measurement requirements before costing any accepted
change. The current A and B electrical platforms must continue to match.

## Quantity is a cash-versus-evidence decision

Reducing 5 + 5 to 3 + 3 removes four fitted BOMs: **${4 * bom_cost(d)[0]:.2f}–
${4 * bom_cost(d)[1]:.2f}** under the old component allowances. It does not
necessarily remove setup or minimum fabrication costs. More units may lower
unit price while increasing total cash, and supplier attrition is additional.

The A/B plan in [docs/50](50-thermal-ab-test-plan.md) calls for five samples per
variant. Three per variant are an initial screen; agree how to replace failed
units and obtain the remaining data before treating that screen as the planned
thermal qualification. A quoted 3 + 3 option does not silently change that gate.
"""


# --------------------------------------------------------------------------
# Bare-PCB-only fabrication at 3 boards
# --------------------------------------------------------------------------
OSHPARK_USD_PER_IN2 = 10.0       # 4-layer prototype service, includes 3 copies


def fab3_table() -> str:
    a, b = VARIANTS["a"], VARIANTS["b"]
    o = ["| Board | Size | Area | OSH Park 4-layer (3 copies) | Per board |",
         "|---|---|---:|---:|---:|"]
    total = 0.0
    for v in (a, b):
        in2 = (v.width / 25.4) * (v.height / 25.4)
        price = in2 * OSHPARK_USD_PER_IN2
        total += price
        o.append(f"| {v.key.upper()} — {v.name} | {v.width:.0f} × {v.height:.0f} mm "
                 f"| {in2:.2f} in² | ${price:.2f} | ${price / 3:.2f} |")
    o.append(f"| **Both, 3 + 3 = 6 boards** | | | **${total:.2f}** | "
             f"**${total / 6:.2f}** |")
    return "\n".join(o)


if __name__ == "__main__":
    if "--write" in sys.argv:
        (ROOT / "docs" / "60-manufacturing-cost.md").write_text(report())
        print("wrote docs/60-manufacturing-cost.md")
        (ROOT / "docs" / "61-cost-reduction.md").write_text(reduction_report())
        print("wrote docs/61-cost-reduction.md")
    else:
        print(report())
        print(reduction_report())
