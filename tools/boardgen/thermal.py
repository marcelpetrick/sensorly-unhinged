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
from .design import BOARD_THICKNESS, STACKUP
from .route import ISLAND_WIDTH

T_CU = next(t for name, _, t, _ in STACKUP if name == "F.Cu") * 1e-3
T_PCB = BOARD_THICKNESS * 1e-3
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
                                  n_cu_layers=4, cu_width_m=ISLAND_WIDTH * 1e-3)
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
    lines = [
        "### Hypothetical slab comparison — not the routed board", "",
        "A's generated sensor quiet zone excludes pours on all four layers.",
        "The full-width copper slab below therefore overstates its copper path.",
        "Its ratio is NOT actual A/B isolation or a prediction of accuracy.", "",
        "| Idealized path | Conductance |", "|---|---:|",
        f"| Full-width A-sized slab, FR-4 | {m['a_fr4']*1e3:.2f} mW/K |",
        f"| Full-width A-sized slab, copper | {m['a_cu']*1e3:.1f} mW/K |",
        f"| Full-width slab total | {m['a_total']*1e3:.0f} mW/K |",
        f"| B neck FR-4 | {m['neck_fr4']*1e3:.2f} mW/K |",
        f"| Four {ISLAND_WIDTH:.2f} mm traces | {m['neck_cu']*1e3:.2f} mW/K |",
        f"| Neck total | {m['neck_total']*1e3:.2f} mW/K |",
        f"| Hypothetical slab / neck ratio | {m['ratio']:.0f}× |", "",
        "Thickness and trace width come from the shared electrical model.",
        "Conductivity values and convection are explicit engineering assumptions,",
        "not measurements of this laminate or enclosure.", "",
        "### Illustrative convection sensitivity", "",
        "Coupling = G / (G + 2 h area). The two-face assumption ignores case",
        "obstruction. h values are scenarios, not classified room conditions.", "",
        "| h (W/m²·K) | Slab coupling | Neck coupling |", "|---:|---:|---:|",
    ]
    for h in (5, 10, 25):
        ca = m["a_total"]/(m["a_total"] + 2*h*m["a_sensor_area_mm2"]*1e-6)
        cb = m["neck_total"]/(m["neck_total"] + 2*h*m["island_area_mm2"]*1e-6)
        lines.append(f"| {h} | {ca:.2f} | {cb:.2f} |")
    lines += ["", "No measured electronics-to-ambient thermal resistance exists to",
              "derive a chamber temperature rise. Air exchange, rib conduction,",
              "radiation and transients are omitted. No kelvin error or assertion",
              "that A cannot win is justified. Tests 1–4 establish the real result."]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
