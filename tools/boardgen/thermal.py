# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""First-order thermal model of the two floorplans.

Deliberately simple: 1-D conduction through the PCB from the electronics to the
sensor, against natural convection from the sensor's own copper/FR-4 area to
room air.  It is a *screening* model - it tells us the order of magnitude and
which term dominates, which is exactly what a floorplan decision needs.  The
real numbers come from Test 1-4 in docs/50-thermal-ab-test-plan.md.

Run: python -m tools.boardgen.thermal
"""
from __future__ import annotations

import math

K_FR4 = 0.30          # W/m.K, through-plane-ish bulk value for FR-4
K_CU = 385.0          # W/m.K
T_CU = 35e-6          # m, 1 oz finished copper
T_PCB = 1.6e-3        # m
H_CONV = 10.0         # W/m2.K, natural convection, still indoor air, both faces

from .place import place
from .variants import (B_ISLAND_RECT, B_NECK_L, B_NECK_W, VARIANTS)


def conductance_bar(width_m: float, length_m: float, n_cu_layers: float,
                    cu_width_m: float | None = None) -> tuple[float, float]:
    """(FR-4 term, copper term) of a bar of PCB, in W/K."""
    g_fr4 = K_FR4 * (width_m * T_PCB) / length_m
    cw = width_m if cu_width_m is None else cu_width_m
    g_cu = K_CU * (cw * T_CU) * n_cu_layers / length_m
    return g_fr4, g_cu


def island_convection(area_mm2: float) -> float:
    return H_CONV * 2 * area_mm2 * 1e-6        # both faces


def model():
    """Return the screening numbers as a dict."""
    a = VARIANTS["a"]
    placed = {p.ref: p for p in place(a)}
    dist = math.hypot(placed["U4"].x - placed["U2"].x,
                      placed["U4"].y - placed["U2"].y) * 1e-3

    g_fr4, g_cu = conductance_bar(B_NECK_W * 1e-3, B_NECK_L * 1e-3,
                                  n_cu_layers=4, cu_width_m=0.15e-3)
    ix0, iy0, ix1, iy1 = B_ISLAND_RECT
    ga_fr4, ga_cu = conductance_bar(a.width * 1e-3, dist, n_cu_layers=4)
    return {
        "neck_fr4": g_fr4, "neck_cu": g_cu, "neck_total": g_fr4 + g_cu,
        "island_area_mm2": (ix1 - ix0) * (iy1 - iy0),
        "a_fr4": ga_fr4, "a_cu": ga_cu, "a_total": ga_fr4 + ga_cu,
        "a_sensor_area_mm2": a.width * 6.0,
        "a_distance_mm": dist * 1e3,
        "ratio": (ga_fr4 + ga_cu) / (g_fr4 + g_cu),
    }


def report() -> str:
    m = model()
    out = ["### Conduction from the electronics to the sensor", "",
           "| Path | Conductance |", "|---|---:|",
           f"| **A** solid 4-layer board, {m['a_distance_mm']:.0f} mm, FR-4 term "
           f"| {m['a_fr4'] * 1e3:.2f} mW/K |",
           f"| **A** solid 4-layer board, copper term | {m['a_cu'] * 1e3:.1f} mW/K |",
           f"| **A** total | **{m['a_total'] * 1e3:.0f} mW/K** |",
           f"| **B** neck {B_NECK_W} x {B_NECK_L} mm, FR-4 term "
           f"| {m['neck_fr4'] * 1e3:.2f} mW/K |",
           f"| **B** neck, four 0.15 mm traces | {m['neck_cu'] * 1e3:.2f} mW/K |",
           f"| **B** total | **{m['neck_total'] * 1e3:.2f} mW/K** |",
           f"| **Ratio A/B** | **{m['ratio']:.0f}x** |", "",
           "Two things fall out of this table and neither is obvious:", "",
           "1. On Variant A the copper term is "
           f"{m['a_cu'] / m['a_fr4']:.0f}x the FR-4 term. Four plane layers make "
           "the board an isothermal slab; moving the sensor further away on the "
           "*same* copper buys almost nothing.",
           "2. On Variant B the four hair-thin traces still carry "
           f"{m['neck_cu'] / m['neck_fr4']:.0f}x more heat than the entire FR-4 "
           "bridge. Trace width, not slot geometry, is the design lever.", "",
           "### Sensitivity: what the coupling factor actually is", "",
           "Coupling = G_conduction / (G_conduction + G_convection): the fraction "
           "of the electronics' temperature rise that reaches the sensor. The "
           "convection term is the weak part of this model - it depends on vent "
           "geometry and air movement we have not built yet - so it is swept "
           "rather than asserted.", "",
           "| h (W/m^2.K) | condition | A coupling | B coupling |",
           "|---:|---|---:|---:|"]
    for h, label in ((5.0, "sealed, still air"), (10.0, "vented, still room"),
                     (25.0, "vented, light air movement")):
        ga = 2 * h * m["a_sensor_area_mm2"] * 1e-6
        gb = 2 * h * m["island_area_mm2"] * 1e-6
        ca = m["a_total"] / (m["a_total"] + ga)
        cb = m["neck_total"] / (m["neck_total"] + gb)
        out.append(f"| {h:.0f} | {label} | {ca:.2f} | {cb:.2f} |")
    out += ["",
            "**Read it as a ratio, not as an absolute.** Variant A's coupling is "
            "~1.0 under every assumption: the sensor reads the printed circuit "
            "board, not the room, and no plausible vent design changes that. "
            "Variant B's coupling is between 0.1 and 0.4 and *is* sensitive to "
            "the enclosure - which is precisely why the sensor chamber is a "
            "design deliverable and not packaging.", "",
            "With the charger's worst-case 0.40 W (EDS S5.1) lifting the "
            "electronics chamber ~8 K above ambient, that is roughly **7-8 K of "
            "error on A and 1-3 K on B** while charging. Both are large. That is "
            "the finding: *charging is when this product lies to you*, which is "
            "why `PG_N` is wired to a GPIO and why the firmware flags or "
            "suspends readings while USB is present.", "",
            "These are screening estimates - 1-D conduction, lumped convection, "
            "no radiation, no transient behaviour. Their job is to rank the two "
            "geometries and identify the dominant term, not to predict a "
            "measurement. The real numbers come from Test 1-4."]
    return "\n".join(out)


if __name__ == "__main__":
    print(report())
