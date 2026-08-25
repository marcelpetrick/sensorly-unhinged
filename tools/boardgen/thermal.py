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


def report() -> str:
    rows = []

    # --- Variant B: the neck --------------------------------------------
    g_fr4, g_cu = conductance_bar(B_NECK_W * 1e-3, B_NECK_L * 1e-3,
                                  n_cu_layers=4, cu_width_m=0.15e-3)
    g_neck = g_fr4 + g_cu
    ix0, iy0, ix1, iy1 = B_ISLAND_RECT
    island_area = (ix1 - ix0) * (iy1 - iy0)
    g_air_b = island_convection(island_area)
    coupling_b = g_neck / (g_neck + g_air_b)

    # --- Variant A: solid board between the electronics and the sensor ---
    a = VARIANTS["a"]
    placed = {p.ref: p for p in place(a)}
    dist = math.hypot(placed["U4"].x - placed["U2"].x,
                      placed["U4"].y - placed["U2"].y) * 1e-3
    width_a = a.width * 1e-3
    ga_fr4, ga_cu = conductance_bar(width_a, dist, n_cu_layers=4)
    g_a = ga_fr4 + ga_cu
    # the "sensor end" of A that can shed heat to air: the quiet zone strip
    g_air_a = island_convection(a.width * 6.0)
    coupling_a = g_a / (g_a + g_air_a)

    rows.append(("Variant B neck, FR-4 only", g_fr4 * 1e3, "mW/K"))
    rows.append(("Variant B neck, 4 x 0.15 mm copper", g_cu * 1e3, "mW/K"))
    rows.append(("Variant B neck, total", g_neck * 1e3, "mW/K"))
    rows.append(("Variant B island to air", g_air_b * 1e3, "mW/K"))
    rows.append(("Variant B coupling factor", coupling_b, "-"))
    rows.append(("Variant A board path, FR-4", ga_fr4 * 1e3, "mW/K"))
    rows.append(("Variant A board path, 4 copper layers", ga_cu * 1e3, "mW/K"))
    rows.append(("Variant A board path, total", g_a * 1e3, "mW/K"))
    rows.append(("Variant A sensor end to air", g_air_a * 1e3, "mW/K"))
    rows.append(("Variant A coupling factor", coupling_a, "-"))
    rows.append(("Isolation improvement, A/B", g_a / g_neck, "x"))

    out = ["| Quantity | Value | Unit |", "|---|---:|---|"]
    for name, val, unit in rows:
        out.append(f"| {name} | {val:.3g} | {unit} |")

    # what it means for the charger
    p_chg = 0.40                      # W, EDS S5.1 worst case
    rise = 8.0                        # K, assumed electronics-chamber rise
    out.append("")
    out.append(f"With the charger dissipating {p_chg:.2f} W and the electronics "
               f"chamber sitting {rise:.0f} K above ambient, the modelled sensor "
               f"error is **{coupling_a * rise:.1f} K on A** and "
               f"**{coupling_b * rise:.2f} K on B**.")
    return "\n".join(out)


if __name__ == "__main__":
    print(report())
