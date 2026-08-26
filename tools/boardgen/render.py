# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render a variant to SVG - the review drawing, not a manufacturing output.

Shows what a reviewer needs at floorplan stage: outline, the RF and thermal
keep-outs, every courtyard and pad, the reference designators, and the routed
sensor-island nets.
"""
from __future__ import annotations

from pathlib import Path

from . import geometry as G
from .design import PART_BY_REF
from .place import Placement
from .variants import (B_ISLAND_RECT, B_NECK_RECT, Variant, antenna_keepout,
                       sensor_keepout)

SCALE = 12.0          # px per mm
PAD = 14.0            # px border

STYLE = """
.outline{fill:#0d3b26;stroke:#c9d1d9;stroke-width:.18}
.crtyd{fill:none;stroke:#8b98a5;stroke-width:.08;stroke-dasharray:.5 .4;opacity:.75}
.pad{fill:#e3b341}
.pad-b{fill:#6ea8fe;opacity:.85}
.ref{font:600 1.05px ui-sans-serif,system-ui,sans-serif;fill:#e6edf3;
     text-anchor:middle;dominant-baseline:central}
.dim{font:500 1.25px ui-monospace,ui-sans-serif,monospace;fill:#8b949e}
.tag{font:600 1.05px ui-monospace,monospace;fill:#f85149}
.tagb{font:600 1.05px ui-monospace,monospace;fill:#58a6ff}
.rf{fill:#f85149;fill-opacity:.16;stroke:#f85149;stroke-width:.12;
    stroke-dasharray:.7 .5}
.quiet{fill:#58a6ff;fill-opacity:.16;stroke:#58a6ff;stroke-width:.12;
       stroke-dasharray:.7 .5}
.trk{fill:none;stroke:#f0b429;stroke-width:.15;stroke-linecap:round;
     stroke-linejoin:round}
.via{fill:none;stroke:#f0b429;stroke-width:.1}
.hot{fill:#f85149;opacity:.85}
"""

def _rect(x0, y0, x1, y1, cls, extra=""):
    return (f'<rect class="{cls}" x="{x0:.2f}" y="{y0:.2f}" '
            f'width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" {extra}/>')


def render(v: Variant, placed: list[Placement], tracks, vias,
           show_refs=True) -> str:
    w = max(v.width, 27.0) + 2 * PAD / SCALE
    h = v.height + 2 * PAD / SCALE + 3.0
    ox = PAD / SCALE
    oy = PAD / SCALE

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" '
           f'width="{w * SCALE:.0f}" height="{h * SCALE:.0f}" role="img" '
           f'aria-label="Variant {v.key.upper()} floorplan">',
           f"<style>{STYLE}</style>",
           f'<g transform="translate({ox:.2f},{oy:.2f})">']

    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in v.outline)
    out.append(f'<polygon class="outline" points="{pts}"/>')

    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    out.append(_rect(ax0, ay0, ax1, ay1, "rf"))
    out.append(f'<text class="tag" x="{ax0 + 0.5:.2f}" y="{ay1 - 0.9:.2f}" '
               f'style="fill:#f85149">RF KEEP-OUT</text>')

    if v.key == "b":
        nx0, ny0, nx1, ny1 = B_NECK_RECT
        ix0, iy0, ix1, iy1 = B_ISLAND_RECT
        out.append(_rect(ix0, iy0, ix1, iy1, "quiet"))
        out.append(_rect(nx0, ny0, nx1, ny1, "quiet"))
        out.append(f'<text class="tagb" x="{ix0 + 0.5:.2f}" y="{iy1 - 0.7:.2f}">'
                   f'SENSOR ISLAND</text>')
        out.append(f'<text class="tagb" x="{nx1 + 0.6:.2f}" y="{(ny0 + ny1) / 2:.2f}">'
                   f'NECK {nx1 - nx0:.1f} x {ny1 - ny0 - 1:.0f}</text>')
    else:
        sx0, sx1, sy0, sy1 = sensor_keepout(v)
        out.append(_rect(sx0, sy0, sx1, sy1, "quiet"))
        out.append(f'<text class="tagb" x="{sx0 + 0.5:.2f}" y="{sy0 + 1.4:.2f}">'
                   f'SENSOR QUIET ZONE</text>')

    for t in tracks:
        d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in t.pts)
        out.append(f'<path class="trk" d="{d}"/>')
    for vi in vias:
        out.append(f'<circle class="via" cx="{vi.x:.2f}" cy="{vi.y:.2f}" '
                   f'r="{vi.size / 2:.2f}"/>')

    hot = {"U4", "U3", "L1"}
    for p in placed:
        fp = G.get(p.footprint)
        x0, x1, y0, y1 = p.box
        out.append(_rect(x0, y0, x1, y1, "crtyd"))
        cls = "pad-b" if fp.bottom else "pad"
        for name, plist in fp.pads.items():
            wpad, hpad = fp.pad_size.get(name, (0.4, 0.4))
            if p.rot % 180:
                wpad, hpad = hpad, wpad
            for (lx, ly) in plist:
                px, py = G.xform(lx, ly, p.x, p.y, p.rot)
                out.append(_rect(px - wpad / 2, py - hpad / 2,
                                 px + wpad / 2, py + hpad / 2, cls))
        if p.ref in hot:
            out.append(f'<circle class="hot" cx="{p.x:.2f}" cy="{p.y:.2f}" r="0.8"/>')
        if show_refs and not p.ref.startswith("TP"):
            out.append(f'<text class="ref" x="{p.x:.2f}" y="{p.y:.2f}">{p.ref}</text>')

    out.append(f'<text class="dim" x="0" y="-0.6">{v.width:.0f} x {v.height:.0f} mm'
               f'   {v.revision}   {v.name}</text>')
    ly = v.height + 2.2
    legend = [("#e3b341", "top pad"), ("#6ea8fe", "pogo pad"),
              ("#f0b429", "island 0.15"), ("#f85149", "heat source")]
    lx = 0.0
    for colour, label in legend:
        out.append(f'<rect x="{lx:.2f}" y="{ly - 0.9:.2f}" width="1.1" height="1.1" '
                   f'fill="{colour}"/>')
        out.append(f'<text class="dim" x="{lx + 1.6:.2f}" y="{ly:.2f}">{label}</text>')
        lx += 1.7 + len(label) * 0.62
    out.append("</g></svg>")
    return "\n".join(out)


def write(path: Path, svg: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg)
